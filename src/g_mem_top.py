# -----------------------------------------------------------------------------
#  Confidential and Proprietary
#  Copyright (C) 2025 Eyal Hochberg. All rights reserved.
#
#  Unauthorized use, copying, distribution, or modification,
#  in whole or in part, is strictly prohibited without prior written consent.
# -----------------------------------------------------------------------------

"""
g_mem_top module
"""

from p2v import p2v, clk_arst, clk_srst

import g_mem
import g_sram

class g_mem_top(p2v):
    """
    This class creates a single interface for all memory modules.
    """

    def module(self, name=None, sram_name=None, bits=64, line_num=1024,
               sample_rd_out=False, sync_reset=False):
        # pylint: disable=too-many-arguments
        """
        Main function
        """
        if isinstance(line_num, str):
            try: # support string line number line="256*1024"
                line_num = eval(line_num) # pylint: disable=(eval-used
            except RuntimeError:
                pass

        self.set_param(name, [None, str], default=None) # explicitly set module name
        self.set_param(sram_name, [None, str], default=None) # name of sram verilog module, None uses flip-flops
        self.set_param(bits, int, bits > 0) # data width
        self.set_param(line_num, int, line_num > 1) # line number
        self.set_param(sample_rd_out, bool, default=False) # sample read port outputs for better timing
        self.set_param(sync_reset, bool, default=False) # use sync reset instead of async reset
        self.set_modname("")




        clk0, clk1 = self.get_clks(sram_name, sync_reset=sync_reset \
        )

        # common arguments
        args = {}
        args["clk0"] = clk0
        args["clk1"] = clk1
        args["name"] = name
        args["sram_name"] = sram_name
        args["bits"] = bits
        args["line_num"] = line_num


        if True: # pylint: disable=using-constant-test

            g_mem.g_mem(self).module(**args, \
                                     sample_out=sample_rd_out)


    def get_clks(self, sram_name, sync_reset=False \
        ):
        """
        Set clock reset type and prefix according to bus functionality
        """
        sram_params = g_sram.g_sram(self).get_params(sram_name)
        port0_wr = sram_params["port0"] == "w"
        port0_rd = sram_params["port0"] == "r"
        port1_wr = sram_params["port1"] == "w"
        port1_rd = sram_params["port1"] == "r"
        if (port0_rd and port1_rd) or (port0_wr and port1_wr):
            prefix0 = sram_params["port0"]
            prefix1 = sram_params["port1"]
        elif not port1_rd and not port1_wr:
            prefix0 = ""
            prefix1 = ""
        else:
            prefix0 = "clk0"
            prefix1 = "clk1"

        if sync_reset:
            return clk_srst(prefix0), clk_srst(prefix1)
        return clk_arst(prefix0), clk_arst(prefix1)

