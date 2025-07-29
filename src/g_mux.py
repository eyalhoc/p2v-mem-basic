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
g_mux module
"""

from p2v import p2v, misc, clock, default_clk

class g_mux(p2v):
    """
    This class creates a mux.
    Features:
        * multiple ports
        * encoded / decoded selector
        * optional sampling of output
    """
    def module(self, clk=default_clk, num=8, bits=32, encode=True, sample=False, has_valid=False):
        # pylint: disable=too-many-branches
        """
        Main function
        """

        self.set_param(clk, clock) # optional clock
        self.set_param(num, int, num > 0) # number of inputs
        self.set_param(bits, int, bits > 0) # data width
        self.set_param(encode, bool, default=True) # encoded selector or hot-one decoded selector
        self.set_param(sample, bool, default=False) # sample output
        self.set_param(has_valid, bool, default=False) # sample has_valid signal
        self.set_modname()


        if encode:
            sel_bits = max(1, misc.log2(num))
        else:
            sel_bits = num

        if sample:
            self.input(clk)
        if has_valid:
            valid = self.input()
            valid_out = self.output()
        else:
            valid = None

        din = {}
        sel = self.input([sel_bits])
        for n in range(num):
            din[n] = self.input([bits])
        out = self.output([bits])


        decoded_sel = self.logic([num])
        if encode:
            for n in range(num):
                self.assign(decoded_sel[n], sel == n)
        else:
            self.assign(decoded_sel, sel)

        sel_lines = []
        for n in range(num):
            sel_bus = misc.concat(bits * [decoded_sel[n]])
            sel_lines.append(sel_bus & din[n])
        mux_lines = misc.concat(sel_lines, sep="|\n")

        self.sample(clk, out, mux_lines, valid=valid, bypass=not sample)
        if has_valid:
            self.sample(clk, valid_out, valid, bypass=not sample)

        if not encode and sample:
            self.assume_property(clk, misc.onehot0(sel), "mux decoded selector must be zero or hotone")

        return self.write()

    def gen(self):
        """
        Reserved gen function.

        Args:
            NA

        Returns:
            Random module parameters.
        """
        args = {}
        args["num"] = self.tb.rand_int(1, 64)
        args["bits"] = self.tb.rand_int(1, 1024)
        args["encode"] = self.tb.rand_bool()
        args["sample"] = self.tb.rand_bool()
        args["has_valid"] = self.tb.rand_bool()
        return args

