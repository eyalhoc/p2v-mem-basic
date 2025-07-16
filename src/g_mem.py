# -----------------------------------------------------------------------------
#  Confidential and Proprietary
#  Copyright (C) 2025 Eyal Hochberg. All rights reserved.
#
#  Unauthorized use, copying, distribution, or modification,
#  in whole or in part, is strictly prohibited without prior written consent.
# -----------------------------------------------------------------------------

"""
g_mem module
"""

from p2v import p2v, misc, clock, clk_arst

import g_mux
import g_mem_row
import g_sram

# TBD - support rd_en for power reduction
# TBD - support back pressure

default_clk0 = clk_arst("port0")
default_clk1 = clk_arst("port1")

MAX_BITS = 8 * 1024
MAX_LINE_NUM = 1024 * 1024

MAX_BITS_PER_BANK = MAX_BITS
MAX_LINES_PER_ROW = 64 * 1024

MAX_BANK_NUM = 128
MAX_ROW_NUM = 128


class g_mem(p2v):
    """
    This class creates a memory wrapper.
    Features:
        * simply specify dimentions of virtual memory (total memory)
        * automatic calculation of row and bank numbers
        * ff or library sram implemetation
        * single or dual ports, each can be read, write or read and write
        * same or different clocks for each port
        * bit select and byte select
        * attribute extraction from library sram
        * optional sampling of output
        * testbench tasks: read, write and load file
    """
    def module(self, clk0=default_clk0, clk1=None, name=None, sram_name=None,
                     bits=32, line_num=4*1024, bit_sel=None, sample_out=False):
        # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
        """
        Main function
        """

        _sram_params = g_sram.g_sram(self).get_params(sram_name)
        if sram_name is not None:
            if not _sram_params["dual_clk"]: # always allow unused clock removal
                clk1 = None
            elif clk1 is None: # add missing clock
                clk1 = default_clk1

        if name is None:
            _modname = None
        else:
            _modname = f"{name}_mem"

        # MODULE PARAMETER DEFINITION
        self.set_param(clk0, clock) # port0 clock
        self.set_param(clk1, [None, clock]) # optional port01 clock
        self.set_param(name, [None, str], default=None) # explicitly set module name
        self.set_param(sram_name, [None, str], default=None) # name of sram verilog module, None uses flip-flops
        self.set_param(bits, int, bits > 0) # data width
        self.set_param(line_num, int, line_num > 1) # line number
        #self.set_param(rd_en, bool, default=False) # partial banks read for power reduction
        self.set_param(bit_sel, [None, int]) # override bit_sel
        self.set_param(sample_out, bool, default=False) # sample read data for better timing
        self.set_modname(_modname)

        rd_en = False # TBD

        # EXTRACT PARAMETERS FROM INTERNAL SRAM
        if sram_name is not None:
            ram_bits = _sram_params["bits"]
            ram_line_num = _sram_params["line_num"]
            port_num = misc.cond(_sram_params["port1"] != "", 2, 1)
            if bit_sel is None:
                bit_sel = _sram_params["bit_sel"]

            self.assert_static(line_num >= ram_line_num, f"line number {line_num} is less than sram line number {ram_line_num}", warning=True)

            bits_roundup = misc.roundup(bits, ram_bits)
            bank_num = bits_roundup // ram_bits
            line_num_roundup = misc.roundup(line_num, ram_line_num)
            row_num = line_num_roundup // ram_line_num

            self.assert_static(bank_num <= MAX_BANK_NUM, f"bank number {bank_num} exceeds maximum of {MAX_BANK_NUM}", warning=True)
            self.assert_static(row_num <= MAX_ROW_NUM, f"row number {row_num} exceeds maximum of {MAX_ROW_NUM}", warning=True)

        else:
            ram_bits = ram_line_num = 0
            bank_num = row_num = 1
            bits_roundup = bits
            line_num_roundup = line_num
            port_num = 2
            if bit_sel is None:
                bit_sel = 1

        self.assert_static(bits <= MAX_BITS, f"data width {bits} exceeds maximum of {MAX_BITS}", warning=True)
        self.assert_static(line_num <= MAX_LINE_NUM, f"line number {line_num} exceeds maximum of {MAX_LINE_NUM}", warning=True)


        gen_rows = [0]


        # EXTERNAL VARIBALES WITH PRE PADDING VALUES
        addr_bits = misc.log2(line_num)


        # SET LOCAL VARIABLES
        if clk1 is None:
            clk1 = clk0

        clks = [clk0, clk1]
        lines_per_row = line_num_roundup // row_num
        bits_per_bank = bits_roundup // bank_num
        row_addr_bits = misc.log2(lines_per_row)
        row_sel_bits = misc.log2(row_num)
        sram_addr_bits = misc.log2(line_num_roundup) - row_sel_bits

        self.assert_static(bits_per_bank <= MAX_BITS_PER_BANK, f"bank bits {bits_per_bank} exceeds maximum of {MAX_BITS_PER_BANK}", warning=True)
        self.assert_static(lines_per_row <= MAX_LINES_PER_ROW, f"row line number {line_num} exceeds maximum of {MAX_LINES_PER_ROW}", warning=True)


        # COMMENT CONFIGURATION
        self.line()
        for idx in range(port_num):
            self.remark(f"sram port {idx}: {_sram_params[f'port{idx}']}")
        self.line()
        self.remark([bank_num, row_num])

        # PARAMETER ASSERTIONS
        self.assert_static((bits_roundup % bank_num) == 0, f"bits {bits_roundup} must divide by bank_num {bank_num}")
        self.assert_static((line_num_roundup % row_num) == 0, f"line_num {line_num_roundup} must divide by row_num {row_num}")
        if row_num > 1:
            self.assert_static(misc.is_pow2(lines_per_row), f"line number per row {lines_per_row} must be power of 2 when using multiple rows")
        if bit_sel > 1: # byte select
            self.assert_static((bits_roundup % bit_sel) == 0, f"byte select can only be used with bits {bits} that divides by {bit_sel}")
            self.assert_static((bits_per_bank % bit_sel) == 0, f"byte select can only be used with bank bits_roundup {bits_per_bank} that divides by {bit_sel}")


        # PORTS
        self.input(clk0)
        if clk1 != clk0:
            self.input(clk1)

        for idx in range(port_num):
            port_type = g_sram.g_sram(self).get_port_type(sram_name, idx=idx)
            if "w" in port_type:
                self.input(f"wr{idx}")
                self.input(f"wr{idx}_addr", [addr_bits])
                self.input(f"wr{idx}_data", [bits])

                if bit_sel == 0:
                    self.logic(f"wr{idx}_sel", [bits], assign=-1)
                elif bit_sel == 1:
                    self.input(f"wr{idx}_sel", [bits])
                else:
                    strb_bits = bits // bit_sel
                    self.input(f"wr{idx}_strb", [strb_bits])
                    self.logic(f"wr{idx}_sel", [bits])
                    for i in range(strb_bits):
                        self.assign(misc.bits(f"wr{idx}_sel", bit_sel, bit_sel*i), misc.concat(bit_sel * [misc.bit(f"wr{idx}_strb", i)]))
                    if (bits % bit_sel) > 0:
                        self.assign(misc.bits(f"wr{idx}_sel", bits % bit_sel, start=strb_bits*bit_sel), misc.concat((bits % bit_sel)*[misc.bit(f"wr{idx}_strb", strb_bits-1)]))
            else:
                self.logic(f"wr{idx}", assign=0)
                self.logic(f"wr{idx}_addr", [addr_bits], assign=0)
                self.logic(f"wr{idx}_data", [bits], assign=0)
                self.logic(f"wr{idx}_sel", [bits], assign=0)

            if "r" in port_type:
                self.input(f"rd{idx}")
                if rd_en:
                    self.input(f"rd{idx}_en", [bank_num])
                self.input(f"rd{idx}_addr", [addr_bits])
                self.output(f"rd{idx}_data", [bits])
                self.output(f"rd{idx}_valid")
            else:
                self.logic(f"rd{idx}", assign=0)
                if rd_en:
                    self.logic(f"rd{idx}_en", [bank_num], assign=0)
                self.logic(f"rd{idx}_addr", [addr_bits], assign=0)
                self.logic(f"rd{idx}_data", [bits])
                self.logic(f"rd{idx}_valid")
                self.allow_unused([f"rd{idx}_data", f"rd{idx}_valid"])


        for idx in range(port_num):
            self.logic(f"rd{idx}_data_pad", [bits_roundup])
            self.assign(f"rd{idx}_data", misc.bits(f"rd{idx}_data_pad", bits))
            if bits_roundup > bits:
                self.allow_unused(misc.bits(f"rd{idx}_data_pad", bits_roundup-bits, start=bits))


        for idx in range(port_num):
            self.logic(f"row_wr{idx}_sel", [row_num])
            self.logic(f"row_rd{idx}_sel", [row_num])
        for y in range(row_num):
            for idx in range(port_num):
                self.logic(f"wr{idx}_y{y}", assign=f"wr{idx} & {misc.bit(f'row_wr{idx}_sel', y)}")
                self.logic(f"rd{idx}_data{y}", [bits_roundup])
                for rd_wr in ["wr", "rd"]:
                    if row_num == 1:
                        self.assign(misc.bit(f"row_{rd_wr}{idx}_sel", y), "1'b1")
                    else:
                        self.assign(misc.bit(f"row_{rd_wr}{idx}_sel", y), f"{misc.bits(f'{rd_wr}{idx}_addr', row_sel_bits, start=sram_addr_bits)} == {misc.dec(y, row_sel_bits)}")

        # INSTANCES OUTPUT
        for idx in range(port_num):
            self.logic(f"rd{idx}_sel", [row_num])
            self.logic(f"rd{idx}_sel_pre", [row_num])
            self.logic(f"rd{idx}_valid_pre")
            for y in range(row_num):
                self.assign(misc.bit(f"rd{idx}_sel_pre", y), misc.bit(f"row_rd{idx}_sel", y))

            self.sample(clks[idx], f"rd{idx}_sel", f"rd{idx}_sel_pre", valid=f"rd{idx}")
            self.sample(clks[idx], f"rd{idx}_valid_pre", f"rd{idx}")

            # READ DATA MUX
            son = g_mux.g_mux(self).module(clks[idx], num=row_num, bits=bits_roundup, encode=False, sample=sample_out, valid=True)
            if sample_out:
                son.connect_in(clks[idx])
            son.connect_in("valid", f"rd{idx}_valid_pre")
            son.connect_in("sel", f"rd{idx}_sel")
            for y in range(row_num):
                son.connect_in(f"in{y}", f"rd{idx}_data{y}")
            son.connect_out("out", f"rd{idx}_data_pad")
            son.connect_out("valid_out", f"rd{idx}_valid")
            son.inst(suffix=idx)

        # G_MEM INSTANCES
        son_name = misc.cond(_modname is None, _modname, f"{_modname}_")
        son = None
        for y in range(row_num):
            if y in gen_rows or son is None:
                son = g_mem_row.g_mem_row(self, register=False).module(clk0, clk1, name=son_name, sram_name=sram_name, \
                                                       bits=bits, line_num=lines_per_row, bit_sel=bit_sel, rd_en=rd_en)
            son.connect_in(clk0)
            if clk1 != clk0:
                son.connect_in(clk1)
            for idx in range(port_num):
                son.connect_in(f"wr{idx}", f"wr{idx}_y{y}")
                if addr_bits > sram_addr_bits:
                    son.connect_in(f"wr{idx}_addr", misc.bits(f"wr{idx}_addr", sram_addr_bits))
                else:
                    son.connect_in(f"wr{idx}_addr", misc.pad(sram_addr_bits-addr_bits, misc.bits(f"wr{idx}_addr", addr_bits)))
                son.connect_in(f"wr{idx}_data", misc.pad(bits_roundup-bits, f"wr{idx}_data"))
                son.connect_in(f"wr{idx}_sel", misc.pad(bits_roundup-bits, f"wr{idx}_sel"))
                son.connect_in(f"rd{idx}", f"rd{idx} & {misc.bit(f'row_rd{idx}_sel', y)}")
                if addr_bits > sram_addr_bits:
                    son.connect_in(f"rd{idx}_addr", misc.bits(f"rd{idx}_addr", sram_addr_bits))
                else:
                    son.connect_in(f"rd{idx}_addr", misc.pad(sram_addr_bits-addr_bits, misc.bits(f"rd{idx}_addr", addr_bits)))
                son.connect_out(f"rd{idx}_data", f"rd{idx}_data{y}")
                son.connect_out(f"rd{idx}_valid", None)
            son.inst(f"g_mem_row{y}")


        # ASSERTIONS
        for idx in range(port_num):
            for rd_wr in ["wr", "rd"]:
                self.assert_never(clks[idx], f"{rd_wr}{idx} & ~|row_{rd_wr}{idx}_sel", \
                                  f"port {idx} {rd_wr} to address 0x%0h detected without any row selected", params=f"{rd_wr}{idx}_addr", name=f"{rd_wr}{idx}_no_row_sel")

        # READ AND WRITE TASKS
        self._tasks(bits=bits_roundup, line_num=line_num_roundup, row_num=row_num, row_sel_bits=row_sel_bits, row_addr_bits=row_addr_bits)

        return self.write()




    def _tasks(self, bits, line_num, row_num, row_sel_bits, row_addr_bits):
        self.tb.syn_off()
        for name in ["write", "read"]:
            self.line(f"""
                        task {name};
                            input [31:0] addr; // larger to allow error
                            {misc.cond(name == "write", "input", "output")} [{bits-1}:0] data;
                            begin
                                {self.check_never(f"addr >= {line_num}", f"{name} address %0d exceeds line number {line_num}", params="addr", fatal=True)}
                        """)
            if row_num == 1:
                row_idx = None
            else:
                row_idx = misc.bits("addr", row_sel_bits, start=row_addr_bits)
            row_addr = misc.pad(32-row_addr_bits, misc.bits("addr", row_addr_bits))
            for y in range(row_num):
                if row_idx is not None:
                    self.line(f"if ({row_idx} == {misc.dec(y, row_sel_bits)})")
                self.line(f"g_mem_row{y}.{name}({row_addr}, data);")
            self.line("""
                            end
                        endtask

                      """)

        self.line(f"""
                    integer line_idx = 0;
                    task write_file;
                        input [128*8-1:0] filename;
                        reg [{bits-1}:0] temp_mem [0:{line_num}-1];
                        reg [{bits-1}:0] line_data;
                        begin
                            $readmemh(filename, temp_mem);
                            for (line_idx = 0; line_idx < {line_num}; line_idx = line_idx + 1)
                            begin
                                line_data = temp_mem[line_idx];
                                write(line_idx, line_data);
                            end
                        end
                    endtask
                """)
        self.tb.syn_on()


    def gen(self, name=None, sram_name=None
                  ):
        """
        Reserved gen function.

        Args:
            sram_name([None, str]): can be overriden by command line -params argument

        Returns:
            Random module parameters.
        """
        if self._args.sim:
            gen_ratio = 8 # for test performance
        else:
            gen_ratio = 1

        args = {}
        if sram_name is None:
            args["bits"] = self.tb.rand_list([self.tb.rand_int(1, 32), self.tb.rand_int(1, MAX_BITS_PER_BANK // gen_ratio)])
            args["line_num"] = self.tb.rand_list([self.tb.rand_int(2, 32), self.tb.rand_int(2, MAX_LINES_PER_ROW // gen_ratio)])
            bit_sel = 1
            dual_clk = self.tb.rand_bool()

        else:
            _sram_params = g_sram.g_sram(self).get_params(sram_name)
            bits_per_bank = _sram_params["bits"]
            ram_addr_bits = _sram_params["addr_bits"]
            dual_clk = _sram_params["dual_clk"]
            bit_sel = _sram_params["bit_sel"]
            lines_per_row = 1 << ram_addr_bits
            bank_num = self.tb.rand_int(1, MAX_BANK_NUM // gen_ratio)

            while bits_per_bank > (MAX_BITS_PER_BANK // gen_ratio):
                bits_per_bank = bits_per_bank // 2
            if bit_sel > 1:
                bits_per_bank = misc.roundup(bits_per_bank, bit_sel)

            while lines_per_row > (MAX_LINES_PER_ROW // gen_ratio):
                lines_per_row = lines_per_row // 2

            args["bits"] = bits_per_bank * bank_num
            while args["bits"] > (MAX_BITS // gen_ratio):
                bank_num = bank_num - 1
                args["bits"] = bits_per_bank * bank_num

            row_num = self.tb.rand_int(1, (MAX_ROW_NUM // gen_ratio))
            if row_num > 1:
                lines_per_row = 1 << misc.log2(lines_per_row) # power of 2
            args["line_num"] = lines_per_row * row_num
            while args["line_num"] > (MAX_LINE_NUM // gen_ratio):
                args["line_num"] = args["line_num"] // 2



        clk0 = self.tb.rand_clock(prefix="clk0")
        clk1 = self.tb.rand_clock(prefix="clk1")

        if dual_clk:
            args["clk0"] = clk0
            args["clk1"] = clk1
        else:
            args["clk0"] = args["clk1"] = clk0


        #args["rd_en"] =  TBD - implement - self.tb.rand_bool()
        args["sample_out"] = self.tb.rand_bool()

        args["sram_name"] = sram_name
        if name is None:
            name = self.tb.rand_list([None, "myproj"])
        args["name"] = name

        return args

