# -----------------------------------------------------------------------------
#  Confidential and Proprietary
#  Copyright (C) 2025 Eyal Hochberg. All rights reserved.
#
#  Unauthorized use, copying, distribution, or modification,
#  in whole or in part, is strictly prohibited without prior written consent.
# -----------------------------------------------------------------------------

"""
g_mem_row module
"""

from p2v import p2v, misc, clock, default_clk

import g_mem
import g_sram

class g_mem_single(p2v):
    """
    This class creates a row of memory wrapper (internal class for g_mem).
    """
    def module(self, clk0=default_clk, clk1=None, name=None, sram_name=None, bits=32, line_num=4*1024, bit_sel=None,
                     _left_col=False, _bottom_line=False
                     ):
        # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
        """
        Main function
        """

        if name is None:
            _modname = None
        else:
            _modname = f"{name}_single" + misc.cond(_bottom_line, "_bottom") + misc.cond(_left_col, "_left")

        # MODULE PARAMETER DEFINITION
        self.set_param(clk0, clock) # write clock
        self.set_param(clk1, [None, clock]) # optional read clock
        self.set_param(name, [None, str], default=None) # explicitly set module name
        self.set_param(sram_name, [None, str], default=None) # name of sram verilog module, None uses flip-flops
        self.set_param(bits, int, bits > 0) # data width - for ff implementation only
        self.set_param(line_num, int, line_num > 1) # line number - for ff implementation only
        self.set_param(bit_sel, [None, int]) # override bit_sel
        self.set_modname(_modname)


        sram_params = g_sram.g_sram(self).get_params(sram_name)
        if sram_name is not None:
            bits = sram_params["bits"]
            line_num = sram_params["line_num"]
            port_num = misc.cond(sram_params["port1"] != "", 2, 1)
        else:
            port_num = 2


        # SET LOCAL VARIABLES
        if clk1 is None:
            clk1 = clk0

        addr_bits = misc.log2(line_num)

        # PORTS
        self.input(clk0)
        if clk1 != clk0:
            self.input(clk1)

        for idx in range(port_num):
            self.input(f"wr{idx}")
            self.input(f"wr{idx}_addr", [addr_bits])
            self.input(f"wr{idx}_data", [bits])
            self.input(f"wr{idx}_sel", [bits])
            self.input(f"rd{idx}")
            self.input(f"rd{idx}_addr", [addr_bits])
            self.output(f"rd{idx}_data", [bits])
            self.output(f"rd{idx}_valid")


        bank_num = row_num = 1
        multi_bits = bits
        multi_line_num = line_num

        if bank_num == row_num == 1:
            pad_bits = pad_lines = 0
            actual_sram_name = sram_name
            son = g_sram.g_sram(self).module(clk0, clk1, sram_name=actual_sram_name, bits=bits, line_num=line_num, pad_bits=pad_bits, pad_lines=pad_lines)
            son.connect_in(clk0)
            if clk1 != clk0:
                son.connect_in(clk1)
            for idx in range(port_num):
                son.connect_in(f"wr{idx}")
                son.connect_in(f"wr{idx}_addr")
                son.connect_in(f"wr{idx}_data")
                son.connect_in(f"wr{idx}_sel")
                son.connect_in(f"rd{idx}")
                son.connect_in(f"rd{idx}_addr")
                son.connect_out(f"rd{idx}_data")
                son.connect_out(f"rd{idx}_valid")
            son.inst("sram")



        # READ AND WRITE TASKS
        self._tasks(bits=bits, line_num=line_num, addr_bits=addr_bits)

        return self.write()


    def _tasks(self, bits, line_num, addr_bits):
        self.tb.syn_off()
        for name in ["write", "read"]:
            self.line(f"""
                        task {name};
                            input [31:0] addr; // larger to allow error
                            {misc.cond(name == "write", "input", "output")} [{bits-1}:0] data;
                            begin
                                {self.check_never(f"addr >= {line_num}", f"{name} address 0x%0h is out of memory size 0x%0h", params=["addr", line_num])}
                                sram.{name}({misc.bits('addr', addr_bits)}, data);
                            end
                        endtask
                    """)
        self.tb.syn_on()

