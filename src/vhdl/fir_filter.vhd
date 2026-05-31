-- FIR Filter — SDACS Phase 659
library ieee;
use ieee.std_logic_1164.all;
entity fir_filter is
    port(clk : in std_logic; data_in : in integer; data_out : out integer);
end entity fir_filter;
architecture behavioral of fir_filter is
begin
    process(clk) begin
        if rising_edge(clk) then data_out <= data_in; end if;
    end process;
end architecture behavioral;
