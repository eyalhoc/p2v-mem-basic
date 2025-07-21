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
g_ff_array module
"""

from p2v import p2v, misc, clock, default_clk

class g_ff_array(p2v):
    """
    This class creates a ff implemented memory.
    Features:
        * configurable dimentions
        * optional seperate clocks for read and write
        * optional sampling of output
        * empty hierarchies to mimic memory path
        * read and write tasks
    """
    def module(self, wr_clk=default_clk, rd_clk=None, depth=128, bits=32, bit_sel=1, sample=True, path="mem"):
        """
        Main function
        """
        if rd_clk is None:
            rd_clk = wr_clk
        self.set_param(wr_clk, clock) # write clock
        self.set_param(rd_clk, clock) # read clock if dual clock is used
        self.set_param(depth, int, bits > 0) # number of array lines
        self.set_param(bits, int, bits > 0) # data width
        self.set_param(bit_sel, int, bit_sel in [0, 1], default=1) # use bit select
        self.set_param(sample, bool, default=True) # sample output
        self.set_param(path, str, misc._is_legal_name(path.split(".")[0])) # instance path to enable mimic of other rtl
        self.set_modname()

        addr_bits = misc.log2(depth)


        self.input(wr_clk)
        if wr_clk != rd_clk:
            self.input(rd_clk)

        wr = self.input()
        wr_addr = self.input([addr_bits])
        wr_data = self.input([bits])
        if bit_sel == 1:
            wr_sel = self.input([bits])
        else:
            wr_sel = self.logic([bits], assign=-1)
        rd = self.input()
        rd_addr = self.input([addr_bits])
        rd_data = self.output([bits])


        if "." in path:
            inst_name = path.split(".")[0]
            path = path.replace(f"{inst_name}.", "", 1)

            son = g_ff_array(self).module(wr_clk, rd_clk, depth=depth, bits=bits, sample=sample, path=path)
            son.connect_auto()
            son.inst(inst_name)

            self._top_tasks(inst_name=inst_name, bits=bits, addr_bits=addr_bits)

        else:
            self.logic(path, (depth, bits)) # multi-dimentional array

            self.sample(wr_clk, misc.bit(path, wr_addr), (wr_sel & wr_data) | (~wr_sel & misc.bit(path, wr_addr)), valid=wr)

            if sample:
                self.sample(rd_clk, rd_data, misc.bit(path, rd_addr), valid=rd)
            else:
                self.assign(rd_data, misc.bit(path, rd_addr))
                self.allow_unused([rd_clk, rd])

            self._rw_tasks(path=path, bits=bits, addr_bits=addr_bits)

        return self.write()


    def _top_tasks(self, inst_name, bits, addr_bits):
        self.tb.syn_off()
        self.line(f"""
                    task write;
                        input [{addr_bits-1}:0] addr;
                        input [{bits-1}:0] data;
                        begin
                            {inst_name}.write(addr, data);
                        end
                    endtask

                    task read;
                        input [{addr_bits-1}:0] addr;
                        output [{bits-1}:0] data;
                        begin
                            {inst_name}.read(addr, data);
                        end
                    endtask
                    """)
        self.tb.syn_on()

    def _rw_tasks(self, path, bits, addr_bits):
        self.tb.syn_off()
        self.line(f"""
                    task write;
                        input [{addr_bits-1}:0] addr;
                        input [{bits-1}:0] data;
                        begin
                            {path}[addr] = data;
                        end
                    endtask

                    task read;
                        input [{addr_bits-1}:0] addr;
                        output [{bits-1}:0] data;
                        logic [{bits-1}:0] data;
                        begin
                            data = {path}[addr];
                        end
                    endtask
                    """)
        self.tb.syn_on()

    def gen(self):
        """
        Reserved gen function.

        Args:
            NA

        Returns:
            Random module parameters.
        """
        args = {}
        dual_clk = self.tb.rand_bool()
        if dual_clk:
            args["wr_clk"] = clock("wr_clk", "wr_clk_rst_n")
            args["rd_clk"] = clock("rd_clk", "rd_clk_rst_n")
        else:
            args["wr_clk"] = args["rd_clk"] = default_clk

        args["depth"] = self.tb.rand_int(1, 8*1024)
        args["bits"] = self.tb.rand_int(1, 128)
        args["bit_sel"] = self.tb.rand_bool()
        args["sample"] = self.tb.rand_bool()

        inst_depth = self.tb.rand_int(1, 8)
        args["path"] = ".".join(inst_depth * ["mem"])

        return args

