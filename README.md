
This is the Basic Tier of the P2V-MEM IP.

Features:
	- simply specify dimentions of virtual memory (total memory)
	- automatic calculation of row and bank numbers
	- ff or library sram implemetation
	- single or dual ports, each can be read, write or read and write
	- same or different clocks for each port
	- bit select and byte select
	- attribute extraction from library sram
	- optional sampling of output
	- testbench tasks: read, write and load file

Unsupported features (contact Eyal Hochberg: eyalhoc@gmail.com for inquires)
	- support tiling different srams for exact size matching
	- hamming code error correction (ECC), two bit detection one bit correction
	- supports optional sampling both input and output of ecc decoder
	- ECC byte access by performing read-modify-write
	- AXI bus interface
	- multiple interfaces with simulatanious access to different parts of memory (different sram rows)

	
