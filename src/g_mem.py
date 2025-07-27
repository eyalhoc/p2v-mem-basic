# ----------------------------------------------------------------------------
#  Copyright (C) 2025 Eyal Hochberg (eyalhoc@gmail.com)
#
#  This file is part of an open-source Python-to-Verilog synthesizable converter.
#
#  Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
#  You may use, modify, and distribute this software in accordance with the GPL-3.0 terms.
#
#  This software is distributed WITHOUT ANY WARRANTY; without even the implied
#  warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GPL-3.0 license for full details: https://www.gnu.org/licenses/gpl-3.0.html
# -----------------------------------------------------------------------------
# 
# This is a reduced version of the P2V-MEM IP.
# For the complete feature set see attached documentation.
# For license inquiries contact Eyal Hochberg: eyalhoc@gmail.com
# 
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
                     bits=32, line_num=1024, bit_sel=None, sample_out=False):
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

        wr       = {}
        wr_addr  = {}
        wr_data  = {}
        wr_sel   = {}
        if bit_sel > 1:
            wr_strb = {}
        rd       = {}
        rd_sel   = {}
        rd_addr  = {}
        rd_data  = {}
        rd_valid = {}
        for idx in range(port_num):
            port_type = g_sram.g_sram(self).get_port_type(sram_name, idx=idx)
            if "w" in port_type:
                wr[idx]         = self.input()
                wr_addr[idx]    = self.input([addr_bits])
                wr_data[idx]    = self.input([bits])

                if bit_sel == 0:
                    wr_sel[idx] = self.logic([bits], assign=-1)
                elif bit_sel == 1:
                    wr_sel[idx] = self.input([bits])
                else:
                    strb_bits = bits // bit_sel
                    wr_strb[idx] = self.input([strb_bits])
                    wr_sel[idx]  = self.logic([bits])
                    for i in range(strb_bits):
                        start = bit_sel * i
                        self.assign(wr_sel[idx][start:start+bit_sel], wr_strb[idx][i] * bit_sel)
                    bit_sel_remain = bits % bit_sel
                    if bit_sel_remain > 0:
                        start = strb_bits * bit_sel
                        self.assign(wr_sel[idx][start:+start+bit_sel_remain], wr_strb[idx][strb_bits-1] * bit_sel_remain)
            else:
                wr[idx]         = self.logic(assign=0)
                wr_addr[idx]    = self.logic([addr_bits], assign=0)
                wr_data[idx]    = self.logic([bits], assign=0)
                wr_sel[idx]     = self.logic([bits], assign=0)

            if "r" in port_type:
                rd[idx]         = self.input()
                if rd_en:
                    rd_sel[idx] = self.input([bank_num])
                rd_addr[idx]    = self.input([addr_bits])
                rd_data[idx]    = self.output([bits])
                rd_valid[idx]   = self.output()
            else:
                rd[idx]         = self.logic(assign=0)
                if rd_en:
                    rd_sel[idx] = self.logic([bank_num], assign=0)
                rd_addr[idx]    = self.logic([addr_bits], assign=0)
                rd_data[idx]    = self.logic([bits])
                rd_valid[idx]   = self.logic()
                self.allow_unused([rd_data[idx], rd_valid[idx]])


        rd_data_pad = {}
        for idx in range(port_num):
            rd_data_pad[idx] = self.logic([bits_roundup])
            self.assign(rd_data[idx], rd_data_pad[idx][:bits])
            if bits_roundup > bits:
                self.allow_unused(rd_data_pad[idx][bits:])


        wr_row_sel = {}
        rd_row_sel = {}
        wr_row = {}
        rd_row_data = {}
        for idx in range(port_num):
            wr_row_sel[idx] = self.logic([row_num])
            rd_row_sel[idx] = self.logic([row_num])
            wr_row[idx] = {}
            rd_row_data[idx] = {}
            for y in range(row_num):
                wr_row[idx][y] = self.logic(assign=wr[idx] & wr_row_sel[idx][y])
                rd_row_data[idx][y] = self.logic([bits_roundup])
                if row_num == 1:
                    self.assign(wr_row_sel[idx][y], 1)
                    self.assign(rd_row_sel[idx][y], 1)
                else:
                    self.assign(wr_row_sel[idx][y], wr_addr[idx][sram_addr_bits:sram_addr_bits+row_sel_bits] == y)
                    self.assign(rd_row_sel[idx][y], rd_addr[idx][sram_addr_bits:sram_addr_bits+row_sel_bits] == y)

        # INSTANCES OUTPUT
        rd_select = {}
        rd_sel_pre = {}
        rd_valid_pre = {}
        for idx in range(port_num):
            rd_select[idx] = self.logic([row_num])
            rd_sel_pre[idx] = self.logic([row_num])
            rd_valid_pre[idx] = self.logic()
            for y in range(row_num):
                self.assign(rd_sel_pre[idx][y], rd_row_sel[idx][y])

            self.sample(clks[idx], rd_select[idx], rd_sel_pre[idx], valid=rd[idx])
            self.sample(clks[idx], rd_valid_pre[idx], rd[idx])

            # READ DATA MUX
            son = g_mux.g_mux(self).module(clks[idx], num=row_num, bits=bits_roundup, encode=False, sample=sample_out, has_valid=True)
            if sample_out:
                son.connect_in(clks[idx])
            son.connect_in(son.valid, rd_valid_pre[idx])
            son.connect_in(son.sel, rd_select[idx])
            for y in range(row_num):
                son.connect_in(son.din[y], rd_row_data[idx][y])
            son.connect_out(son.out, rd_data_pad[idx])
            son.connect_out(son.valid_out, rd_valid[idx])
            son.inst(suffix=idx)

        # # G_MEM INSTANCES
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
                son.connect_in(wr[idx], wr_row[idx][y])
                if addr_bits > sram_addr_bits:
                    son.connect_in(wr_addr[idx], wr_addr[idx][:sram_addr_bits])
                else:
                    son.connect_in(wr_addr[idx], misc.pad(sram_addr_bits-addr_bits, wr_addr[idx][:addr_bits]))
                son.connect_in(wr_data[idx], misc.pad(bits_roundup-bits, wr_data[idx]))
                son.connect_in(wr_sel[idx], misc.pad(bits_roundup-bits, wr_sel[idx]))
                son.connect_in(rd[idx], rd[idx] & rd_row_sel[idx][y])
                if addr_bits > sram_addr_bits:
                    son.connect_in(rd_addr[idx], rd_addr[idx][:sram_addr_bits])
                else:
                    son.connect_in(rd_addr[idx], misc.pad(sram_addr_bits-addr_bits, rd_addr[idx][:addr_bits]))
                son.connect_out(rd_data[idx], rd_row_data[idx][y])
                son.connect_out(rd_valid[idx], None)
            son.inst(f"g_mem_row{y}")


        # ASSERTIONS
        for idx in range(port_num):
            self.assert_never(clks[idx], wr[idx] & (wr_row_sel[idx] == 0), \
                              f"port {idx} write to address 0x%0h detected without any row selected", params=wr_addr[idx], name=f"wr{idx}_no_row_sel")
            self.assert_never(clks[idx], rd[idx] & (rd_row_sel[idx] == 0), \
                              f"port {idx} read to address 0x%0h detected without any row selected", params=rd_addr[idx], name=f"rd{idx}_no_row_sel")

        # READ AND WRITE TASKS
        self._tasks(bits=bits_roundup, line_num=line_num_roundup, row_num=row_num, row_sel_bits=row_sel_bits, row_addr_bits=row_addr_bits)

        return self.write()




    def _tasks(self, bits, line_num, row_num, row_sel_bits, row_addr_bits):
        self.tb.syn_off()
        for name in ["write", "read"]:
            self.line(f"""
                        task automatic {name};
                            input [31:0] addr; // larger to allow error
                            {misc.cond(name == "write", "input", "output")} [{bits-1}:0] data;
                            begin
                                {self.check_never(f"addr >= {line_num}", f"{name} address %0d exceeds line number {line_num}", params="addr", fatal=True)}
                        """)
            if row_num == 1:
                row_idx = None
            else:
                row_idx = misc._declare("addr", row_sel_bits, start=row_addr_bits)
            row_addr = misc.pad(32-row_addr_bits, misc._declare("addr", row_addr_bits))
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
                    task automatic write_file;
                        input [128*8-1:0] filename;
                        reg [{bits-1}:0] temp_mem [{line_num}];
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

