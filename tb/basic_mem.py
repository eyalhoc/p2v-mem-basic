# -----------------------------------------------------------------------------
#  Confidential and Proprietary
#  Copyright (C) 2025 Eyal Hochberg. All rights reserved.
#
#  Unauthorized use, copying, distribution, or modification, 
#  in whole or in part, is strictly prohibited without prior written consent.
# -----------------------------------------------------------------------------

from p2v import p2v

import g_mem_top

class basic_mem(p2v):
    
    def module(self, project="carmel"):


        # main sram
        g_mem_top.g_mem_top(self).module(name=f"{project}_main", bits=64, line_num=4*1024, sram_name="sram_1rw1r0w_32_512_scn4m_subm", sample_rd_out=True)  
        # local sram - ff implementation
        g_mem_top.g_mem_top(self).module(name=f"{project}_local", bits=17, line_num=64)      
        
