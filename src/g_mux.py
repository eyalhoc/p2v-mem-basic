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

from p2v import p2v, misc, clock, default_clk, p2v_enum

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

        _input_names = []
        if isinstance(num, p2v_enum):
            _enum_name = num.NAME
            for _name in vars(num):
                if not _name.startswith("__") and _name not in ["NAME", "BITS"]:
                    _input_names.append(_name)
            if not misc.is_pow2(len(_input_names)):
                _input_names.append("DEFAULT")
            num = len(_input_names)
        else:
            _enum_name = ""
            for _n in range(num):
                _input_names.append(f"din{_n}")

        if isinstance(bits, p2v_enum):
            bits = bits.BITS


        self.set_param(clk, clock) # optional clock
        self.set_param(num, int, num > 0, suffix=_enum_name) # number of inputs or enumerated type
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

        sel = self.input([sel_bits])
        self.input(_input_names, [bits])
        out = self.output([bits])


        decoded_sel = self.logic([num])
        if encode:
            for n in range(num):
                self.assign(misc.bit(decoded_sel, n), sel == misc.dec(n, sel_bits))
        else:
            self.assign(decoded_sel, sel)

        sel_lines = []
        for n in range(num):
            sel_bus = misc.concat(bits * [misc.bit(decoded_sel, n)])
            sel_lines.append(f"{sel_bus} & {_input_names[n]}")
        mux_lines = " |\n ".join(sel_lines)

        self.sample(clk, out, mux_lines, valid=valid, bypass=not sample)
        if has_valid:
            self.sample(clk, valid_out, valid, bypass=not sample)

        if not encode:
            self.assert_always(sel, misc.is_hotone(sel, sel_bits, allow_zero=True), "mux decoded selector must be hotone")

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

