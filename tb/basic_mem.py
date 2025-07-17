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


from p2v import p2v

import g_mem_top

class basic_mem(p2v):
    
    def module(self, project="carmel"):


        # main sram
        g_mem_top.g_mem_top(self).module(name=f"{project}_main", bits=64, line_num=4*1024, sram_name="sram_1rw1r0w_32_512_scn4m_subm", sample_rd_out=True)  
        # local sram - ff implementation
        g_mem_top.g_mem_top(self).module(name=f"{project}_local", bits=17, line_num=64)      
        
