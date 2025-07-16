# -----------------------------------------------------------------------------
#  Confidential and Proprietary
#  Copyright (C) 2025 Eyal Hochberg. All rights reserved.
#
#  Unauthorized use, copying, distribution, or modification,
#  in whole or in part, is strictly prohibited without prior written consent.
# -----------------------------------------------------------------------------

"""
g_mux module
"""

from p2v import p2v, misc, clock, default_clk, ENUM_NAME, ENUM_BITS, ENUM_DEFAULT

class g_mux(p2v):
    """
    This class creates a mux.
    Features:
        * multiple ports
        * encoded / decoded selector
        * optional sampling of output
    """
    def module(self, clk=default_clk, num=8, bits=32, encode=True, sample=False, valid=False):
        # pylint: disable=too-many-branches
        """
        Main function
        """

        _input_names = []
        if isinstance(num, dict):
            self._assert(ENUM_NAME in num and ENUM_BITS in num, f"{num} is of type dict but it is not a p2v enum", fatal=True)
            _enum_name = num[ENUM_NAME]
            for _name in num:
                if not _name.startswith("__"):
                    _input_names.append(_name)
            if not misc.is_pow2(len(_input_names)):
                _input_names.append(ENUM_DEFAULT)
            num = len(_input_names)
        else:
            _enum_name = ""
            for _n in range(num):
                _input_names.append(f"in{_n}")

        if isinstance(bits, dict):
            self._assert(ENUM_NAME in bits and ENUM_BITS in bits, f"{bits} is of type dict but it is not a p2v enum", fatal=True)
            bits = bits[ENUM_BITS]


        self.set_param(clk, clock) # optional clock
        self.set_param(num, int, num > 0, suffix=_enum_name) # number of inputs or enumerated type
        self.set_param(bits, int, bits > 0) # data width
        self.set_param(encode, bool, default=True) # encoded selector or hot-one decoded selector
        self.set_param(sample, bool, default=False) # sample output
        self.set_param(valid, bool, default=False) # sample valid signal
        self.set_modname()


        if encode:
            sel_bits = max(1, misc.log2(num))
        else:
            sel_bits = num

        if sample:
            self.input(clk)
        if valid:
            self.input("valid")
            self.output("valid_out")

        self.input("sel", [sel_bits])
        for name in _input_names:
            self.input(name, [bits])
        self.output("out", [bits])


        self.logic("decoded_sel", [num])
        if encode:
            for n in range(num):
                self.assign(misc.bit("decoded_sel", n), f"sel == {misc.dec(n, sel_bits)}")
        else:
            self.assign("decoded_sel", "sel")

        sel_lines = []
        for n in range(num):
            sel_bus = misc.concat(bits * [misc.bit("decoded_sel", n)])
            sel_lines.append(f"({sel_bus} & {_input_names[n]})")
        mux_lines = " |\n ".join(sel_lines)

        if sample:
            self.sample(clk, "out", mux_lines, valid=misc.cond(valid, "valid", None))
            if valid:
                self.sample(clk, "valid_out", "valid")
        else:
            self.assign("out", mux_lines)
            if valid:
                self.assign("valid_out", "valid")

        if not encode:
            self.assert_always("sel", misc.is_hotone("sel", sel_bits, allow_zero=True), "mux decoded selector must be hotone")

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
        args["valid"] = self.tb.rand_bool()
        return args

