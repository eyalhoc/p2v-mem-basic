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
g_sram module
"""

from p2v import p2v, clock, misc, default_clk

import g_ff_array

MAX_PORTS = 2

class g_sram(p2v):
    """
    This class creates an sram wrapper.
    Features:
        * multiple ports
        * support TSMC and OpenRam libraries
        * supports flip-flop implementation
    """
    def module(self, clk0=default_clk, clk1=default_clk, sram_name=None, \
               bits=32, line_num=4*1024, bit_sel=None, pad_bits=0, pad_lines=0):
        # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
        """
        Main function
        """

        _sram_params = self.get_params(sram_name)
        if sram_name is None:
            _addr_bits = misc.log2(line_num)
        else:
            bits = _sram_params["bits"]
            _addr_bits = _sram_params["addr_bits"]
        if bit_sel is None:
            bit_sel = _sram_params["bit_sel"]

        line_num = (1 << _addr_bits) + pad_lines

        self.set_param(clk0, clock) # port0 clock
        self.set_param(clk1, [None, clock]) # port1 clock
        self.set_param(sram_name, [str, None]) # sram Verilog module name, None is ff implementation
        self.set_param(bits, int, bits > 0) # data width
        self.set_param(line_num, int, line_num > 1) # line numeber
        self.set_param(bit_sel, [None, int]) # override bit_sel
        self.set_param(pad_bits, int, default=0) # pad data bits
        self.set_param(pad_lines, int, default=0) # pad sram lines
        self.set_modname()

        clks = [clk0, clk1]
        addr_bits = _addr_bits
        pad_addr_bits = misc.log2(line_num) - addr_bits

        self.line()
        for n in range(MAX_PORTS):
            self.remark(f"sram port {n}: {_sram_params[f'port{n}']}")
        self.line()

        wr       = [None] * MAX_PORTS
        wr_addr  = [None] * MAX_PORTS
        wr_data  = [None] * MAX_PORTS
        wr_sel   = [None] * MAX_PORTS
        rd       = [None] * MAX_PORTS
        rd_addr  = [None] * MAX_PORTS
        rd_data  = [None] * MAX_PORTS
        rd_valid = [None] * MAX_PORTS
        
        port_idxs = []
        for n in range(MAX_PORTS):
            port = _sram_params[f"port{n}"]
            if port != "":
                port_idxs.append(n)
                if clks[n] is not None and (n==0 or clks[n] != clks[n-1]):
                    self.input(clks[n])
                wr[n]      = self.input(f"wr{n}")
                wr_addr[n] = self.input(f"wr{n}_addr", [addr_bits+pad_addr_bits])
                wr_data[n] = self.input(f"wr{n}_data", [bits+pad_bits])
                wr_sel[n]  = self.input(f"wr{n}_sel", [bits+pad_bits])
                if bit_sel == 0:
                    self.allow_unused(wr_sel[n])
                rd[n]       = self.input(f"rd{n}")
                rd_addr[n]  = self.input(f"rd{n}_addr", [addr_bits+pad_addr_bits])
                rd_data[n]  = self.output(f"rd{n}_data", [bits+pad_bits])
                rd_valid[n] = self.output(f"rd{n}_valid")
                

        if sram_name is None:
            son = g_ff_array.g_ff_array(self).module(wr_clk=clks[0], rd_clk=clks[1], depth=line_num, bits=bits, sample=True)
            son.connect_in(clks[0])
            if clks[0] != clks[1]:
                son.connect_in(clks[1])
            son.connect_in(son.wr, wr[0])
            son.connect_in(son.wr_addr, wr_addr[0])
            son.connect_in(son.wr_data, wr_data[0])
            son.connect_in(son.wr_sel, wr_sel[0])
            son.connect_in(son.rd, rd[1])
            son.connect_in(son.rd_addr, rd_addr[1])
            son.connect_out(son.rd_data, rd_data[1])
            son.inst("sram")
            path = "sram.mem"


        else:
            # create write select
            wsel = [None] * MAX_PORTS
            for n in range(MAX_PORTS):
                port = _sram_params[f"port{n}"]
                if "w" in port and bit_sel > 0:
                    wsel[n] = self.logic(f"wsel{n}", bits // bit_sel)
                    if bit_sel == 1:
                        self.assign(wsel[n], misc.bits(wr_sel[n], bits))
                    else:
                        for i in range(bits // bit_sel):
                            self.assign(misc.bit(wsel[n], i), misc.bits(wr_sel[n], bit_sel, bit_sel*i) > 0)
    
            signals = self._get_verilog_ports(sram_name)
            names = self._get_lib_names(signals)
            conn = self._get_lib_conn(signals, wr, wr_addr, wr_data, wsel, rd, rd_addr, rd_data)

            addr = [None] * MAX_PORTS
            son = self.verilog_module(sram_name)
            for n in port_idxs:
                addr[n] = self.logic(f"addr{n}", [addr_bits+pad_addr_bits])
                self.assign(addr[n], conn[f"addr{n}"])
                son.connect_in(names[f"clk{n}"], clks[n].name)
                son.connect_in(names[f"addr{n}"], misc.bits(addr[n], addr_bits))
                if self._check_port(sram_name, f"csb{n}"):
                    son.connect_in(names[f"csb{n}"], conn[f"csb{n}"])
                if self._check_port(sram_name, f"web{n}"):
                    son.connect_in(names[f"web{n}"], conn[f"web{n}"])
                if self._check_port(sram_name, f"din{n}"):
                    son.connect_in(names[f"din{n}"], misc.bits(conn[f"din{n}"], bits))
                if self._check_port(sram_name, f"wsel{n}"):
                    son.connect_in(names[f"wsel{n}"], conn[f"wsel{n}"])
                if self._check_port(sram_name, f"dout{n}"):
                    son.connect_out(names[f"dout{n}"], misc.bits(rd_data[n], bits))
                    if pad_bits > 0:
                        self.assign(misc.bits(rd_data[n], pad_bits, start=bits), misc.dec(0, pad_bits))

            # connect unused signals
            for name, signal in signals.items():
                if name not in son._pins:
                    if signal._kind == "input":
                        son.connect_in(name, 0)
                    elif signal._kind == "output":
                        son.connect_out(name, None)

            son.inst("sram")
            path = f"sram.{names['mem']}"


        for n in port_idxs:
            port = _sram_params[f"port{n}"]
            if "w" not in port:
                self.allow_unused(wr[n])
                self.allow_unused(wr_addr[n])
                self.allow_unused(wr_data[n])
                self.allow_unused(wr_sel[n])
                self.assert_never(clks[n], wr[n], f"write detected on read only port {n}")
            if "r" in port:
                self.sample(clks[n], rd_valid[n], rd[n])
            else:
                self.allow_unused(rd[n])
                self.allow_unused(rd_addr[n])
                self.assert_never(clks[n], rd[n], f"read detected on write only port {n}")
                self.assign(rd_data[n], 0)
                self.assign(rd_valid[n], 0)


        self.tb.syn_off()
        self.line(f"""
                    task automatic write;
                        input [{addr_bits+pad_addr_bits-1}:0] addr;
                        input [{bits+pad_bits-1}:0] data;
                        begin
                            {path}[{misc.bits("addr", addr_bits)}] = {misc.bits("data", bits)};
                        end
                    endtask

                    task automatic read;
                        input [{addr_bits+pad_addr_bits-1}:0] addr;
                        output [{bits+pad_bits-1}:0] data;
                        logic [{bits+pad_bits-1}:0] data;
                        begin
                            data = {misc.pad(pad_bits, f"{path}[{misc.bits('addr', addr_bits)}]")};
                        end
                    endtask
                    """)
        self.tb.syn_on()

        return self.write()


    def _get_lib_names(self, signals):
        names = {}

        # openram
        if "din0" in signals and "addr0" in signals:
            names["mem"] = "mem"
            for n in range(MAX_PORTS):
                names[f"clk{n}"]  = f"clk{n}"
                names[f"csb{n}"]  = f"csb{n}"
                names[f"web{n}"]  = f"web{n}"
                names[f"din{n}"]  = f"din{n}"
                names[f"addr{n}"] = f"addr{n}"
                names[f"wsel{n}"] = f"wmask{n}"
                names[f"dout{n}"] = f"dout{n}"

        # tsmc
        elif "D" in signals and "Q" in signals:
            names["mem"] = "u_ram_core.memory"
            if "AA" in signals and "CLKW" in signals: # one write port and one read port
                names["clk0"]  = "CLKW"
                names["csb0"]  = None
                names["web0"]  = "WEB"
                names["addr0"] = "AA"
                names["din0"]  = "D"
                names["wsel0"] = "BWEB"
                names["dout0"] = None

                names["clk1"]  = "CLKR"
                names["csb1"]  = None
                names["web1"]  = "REB"
                names["addr1"] = "AB"
                names["din1"]  = None
                names["wsel1"] = None
                names["dout1"] = "Q"
            else: # one port for read and write
                names["clk0"]  = "CLK"
                names["csb0"]  = "CEB"
                names["web0"]  = "WEB"
                names["addr0"] = "A"
                names["din0"]  = "D"
                names["wsel0"] = "BWEB"
                names["dout0"] = "Q"

                names["clk1"]  = None
                names["csb1"]  = None
                names["web1"]  = None
                names["addr1"] = None
                names["din1"] = None
                names["wsel1"] = None
                names["dout1"] = None

        else:
            self._raise("failed to find sram port connectivity")

        return names

    def _get_lib_conn(self, signals, wr, wr_addr, wr_data, wsel, rd, rd_addr, rd_data):
        conn = {}

        # openram
        if "din0" in signals and "addr0" in signals:
            conn["mem"] = "mem"
            for n in range(MAX_PORTS):
                if wr[n] is None:
                    continue
                conn[f"clk{n}"]  = None
                conn[f"csb{n}"]  = ~(wr[n] | rd[n])
                conn[f"web{n}"]  = rd[n]
                conn[f"din{n}"]  = wr_data[n]
                conn[f"addr{n}"] = misc.cond(wr[n], wr_addr[n], rd_addr[n])
                conn[f"wsel{n}"] = wsel[n]
                conn[f"dout{n}"] = None

        # tsmc
        elif "D" in signals and "Q" in signals:
            conn["mem"] = "u_ram_core.memory"
            if "AA" in signals and "CLKW" in signals: # one write port and one read port
                conn["clk0"]  = None
                conn["csb0"]  = None
                conn["web0"]  = wr[0]
                conn["addr0"] = wr_addr[0]
                conn["din0"]  = wr_data[0]
                conn["wsel0"] = wsel[0]
                conn["dout0"] = None

                conn["clk1"]  = None
                conn["csb1"]  = None
                conn["web1"]  = rd[1]
                conn["addr1"] = rd_addr[1]
                conn["din1"]  = None
                conn["wsel1"] = None
                conn["dout1"] = None
            else: # one port for read and write
                conn["clk0"]  = None
                conn["csb0"]  = ~(wr[0] | rd[0])
                conn["web0"]  = rd[0]
                conn["addr0"] = misc.cond(wr[0], wr_addr[0], rd_addr[0])
                conn["din0"]  = wr_data[0]
                conn["wsel0"] = ~wsel[0]
                conn["dout0"] = rd_data[0]

                conn["clk1"]  = None
                conn["csb1"]  = None
                conn["web1"]  = None
                conn["addr1"] = None
                conn["din1"] = None
                conn["wsel1"] = None
                conn["dout1"] = None

        else:
            self._raise("failed to find sram port connectivity")

        return conn
        
    def _check_port(self, sram_name, name):
        signals = self._get_verilog_ports(sram_name)
        names = self._get_lib_names(signals)
        port_names = list(signals.keys())
        return names[name] is not None and names[name] in port_names


    def get_params(self, sram_name):
        """
        Get dictionary of sram parameters.

        Args:
            sram_name([str, None]): sram_name, None is ff implementation

        Returns:
            dict
        """
        if sram_name is None:
            return {"port0":"w", "port1":"r","bit_sel":1}
        params = {}
        self._assert_type(sram_name, str)
        self.assert_static(self._find_module(sram_name) is not None, f"could not find sram {sram_name}")
        signals = self._get_verilog_ports(sram_name)
        names = self._get_lib_names(signals)

        params["bits"] = signals[names["din0"]]._bits
        params["addr_bits"] = signals[names["addr0"]]._bits
        params["line_num"] = 1 << params["addr_bits"]
        port_names = list(signals.keys())
        params["dual_clk"] = names["clk1"] in port_names
        if names["wsel0"] in port_names:
            params["bit_sel"] = params["bits"] // signals[names["wsel0"]]._bits
        else:
            params["bit_sel"] = 0

        for n in range(MAX_PORTS):
            params[f"port{n}"] = self.get_port_type(sram_name, idx=n)

        return params

    def get_port_type(self, sram_name, idx):
        """
        Get read / write type for a port.

        Args:
            sram_name(str): sram_name
            idx(int): port index

        Returns:
            string ("w", "r" or "w/r")
        """
        if sram_name is None:
            params = self.get_params(sram_name)
        else:
            params = {}
            for n in range(MAX_PORTS):
                if self._check_port(sram_name, f"csb{n}") and self._check_port(sram_name, f"web{n}"):
                    params[f"port{n}"] = "w/r"
                elif self._check_port(sram_name, f"csb{n}") or self._check_port(sram_name, f"web{n}"):
                    if self._check_port(sram_name, f"din{n}"):
                        params[f"port{n}"] = "w"
                    else:
                        params[f"port{n}"] = "r"
                else:
                    params[f"port{n}"] = ""
        return params[f"port{idx}"]

    def compare_srams(self, sram_name0, sram_name1, allow_diff=None):
        """
        Compare atributes of 2 srams and allow differences in specific parameters.

        Args:
            sram_name0(str): first sram name
            sram_name1(str): second sram name
            allow_diff(list): list of parameters to allow differences

        Returns:
            NA (errors out)
        """
        if allow_diff is None:
            allow_diff = []
        self._assert_type(sram_name0, str)
        self._assert_type(sram_name1, str)
        self._assert_type(allow_diff, list)
        other_params = g_sram(self).get_params(sram_name1)
        for name, value in self.get_params(sram_name0).items():
            if name not in allow_diff:
                self.assert_static(value == other_params[name], f"{sram_name0} uses ({name} = {value}) while {sram_name1} uses ({name} = {other_params[name]})")

