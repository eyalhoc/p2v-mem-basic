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
g_mem_row module
"""

from p2v import p2v, misc, clock, default_clk

import g_sram
import g_mem_single

class g_mem_row(p2v):
    """
    This class creates a row of memory wrapper (internal class for g_mem).
    """
    def module(self, clk0=default_clk, clk1=None, name=None, sram_name=None, bits=32, line_num=4*1024, bit_sel=None, rd_en=False,
               _bottom_line=False
                ):
        # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
        """
        Main function
        """

        if name is None:
            _modname = None
        else:
            _modname = f"{name}_row" + misc.cond(_bottom_line, "_bottom")

        # MODULE PARAMETER DEFINITION
        self.set_param(clk0, clock) # write clock
        self.set_param(clk1, [None, clock]) # optional read clock
        self.set_param(name, [None, str], default=None) # explicitly set module name
        self.set_param(sram_name, [None, str], default=None) # name of sram verilog module, None uses flip-flops
        self.set_param(bits, int, bits > 0) # data width - for ff implementation only
        self.set_param(line_num, int, line_num > 1) # line number - for ff implementation only
        self.set_param(bit_sel, [None, int]) # override bit_sel
        self.set_param(rd_en, bool, default=False) # partial banks read for power reduction
        self.set_modname(_modname)


        bank_num = 1
        port_num = 2
        pad_left = 0
        gen_banks = [0]
        sram_params = g_sram.g_sram(self).get_params(sram_name)
        if sram_name is not None:
            line_num = sram_params["line_num"]
            port_num = misc.cond(sram_params["port1"] != "", 2, 1)
            ram_bits = sram_params["bits"]
            bits_roundup = misc.roundup(bits, ram_bits)
            bank_num = bits_roundup // ram_bits
            bits = bits_roundup




        # SET LOCAL VARIABLES
        if clk1 is None:
            clk1 = clk0

        clks = [clk0, clk1]
        addr_bits = misc.log2(line_num)
        bits_per_bank = bits // bank_num

        # PORTS
        self.input(clk0)
        if clk1 != clk0:
            self.input(clk1)

        wr       = []
        wr_addr  = []
        wr_data  = []
        wr_sel   = []
        rd       = []
        rd_sel   = []
        rd_addr  = []
        rd_data  = []
        rd_valid = []
        for idx in range(port_num):
            wr       += [self.input(f"wr{idx}")]
            wr_addr  += [self.input(f"wr{idx}_addr", [addr_bits])]
            wr_data  += [self.input(f"wr{idx}_data", [bits])]
            wr_sel   += [self.input(f"wr{idx}_sel", [bits])]
            rd       += [self.input(f"rd{idx}")]
            if rd_en:
                rd_sel += [self.input(f"rd{idx}_en", [bank_num])]
            else:
                rd_sel += [self.logic(f"rd{idx}_en", [bank_num], assign=-1)]
            rd_addr  += [self.input(f"rd{idx}_addr", [addr_bits])]
            rd_data  += [self.output(f"rd{idx}_data", [bits])]
            rd_valid += [self.output(f"rd{idx}_valid")]


        bank_wr_sel = [None] * port_num
        bank_rd_sel = [None] * port_num
        wr_bank = {}
        wr_bank_sel = {}
        for idx in range(port_num):
            bank_wr_sel[idx] = self.logic(f"wr{idx}_bank_sel", [bank_num])
            bank_rd_sel[idx] = self.logic(f"rd{idx}_bank_sel", [bank_num])
            wr_bank[idx] = [None] * bank_num
            wr_bank_sel[idx] = [None] * bank_num
            for x in range(bank_num):
                wr_bank[idx][x] = self.logic(f"wr{idx}_bank{x}", assign=wr[idx] & misc.bit(bank_wr_sel[idx], x))
                wr_bank_sel[idx][x] = self.logic(f"wr{idx}_sel{x}", [bits_per_bank], assign=misc.bits(wr_sel[idx], bits_per_bank, start=bits_per_bank*x))

                self.assign(misc.bit(bank_wr_sel[idx], x), wr_bank_sel[idx][x]> 0)
                self.assign(misc.bit(bank_rd_sel[idx], x), misc.bit(rd_sel[idx], x))


        # G_MEM INSTANCES
        son_name = misc.cond(_modname is None, _modname, f"{_modname}_")
        son = None
        for x in range(bank_num):
            if x in gen_banks or son is None:
                son = g_mem_single.g_mem_single(self, register=False).module(clk0, clk1, name=son_name, sram_name=sram_name, \
                                                             bits=bits_per_bank, line_num=line_num)
            son.connect_in(clk0)
            if clk1 != clk0:
                son.connect_in(clk1)
            for idx in range(port_num):
                son.connect_in(wr[idx], wr_bank[idx][x])
                son.connect_in(wr_addr[idx], misc.bits(wr_addr[idx], addr_bits))
                son.connect_in(wr_data[idx], misc.bits(wr_data[idx], bits_per_bank, start=bits_per_bank*x))
                son.connect_in(wr_sel[idx], wr_bank_sel[idx][x])
                son.connect_in(rd[idx], rd[idx] & misc.bit(bank_rd_sel[idx], x))
                son.connect_in(rd_addr[idx], misc.bits(rd_addr[idx], addr_bits))
                son.connect_out(rd_data[idx], misc.bits(rd_data[idx], bits_per_bank, start=bits_per_bank*x))
                son.connect_out(rd_valid[idx], None)
            son.inst(f"g_mem_bank{x}")


        for idx in range(port_num):
            self.sample(clks[idx], rd_valid[idx], rd[idx])

            # ASSERTIONS
            self.assert_never(clks[idx], wr[idx] & (bank_wr_sel[idx] == 0), \
                              f"port {idx} write to address 0x%0h detected without any bank selected", params=wr_addr[idx])
            self.assert_never(clks[idx], rd[idx] & (bank_rd_sel[idx] == 0), \
                              f"port {idx} read to address 0x%0h detected without any bank selected", params=rd_addr[idx])


        # READ AND WRITE TASKS
        self._tasks(bits=bits, bank_num=bank_num, bits_per_bank=bits_per_bank)

        return self.write()




    def _tasks(self, bits, bank_num, bits_per_bank):
        self.tb.syn_off()
        for name in ["write", "read"]:
            self.line(f"""
                        task automatic {name};
                            input [31:0] addr; // larger to allow error
                            {misc.cond(name == "write", "input", "output")} [{bits-1}:0] data;
                            begin
                        """)
            for x in range(bank_num):
                self.line(f"g_mem_bank{x}.{name}(addr, {misc.bits('data', bits_per_bank, start=bits_per_bank*x)});")
            self.line("""
                            end
                        endtask
                        """)
        self.tb.syn_on()

