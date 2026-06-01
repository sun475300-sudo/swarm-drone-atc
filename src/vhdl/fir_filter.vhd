-- FIR filter stub for SDACS sensor signal processing — VHDL
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter is
    generic (
        TAPS : integer := 8;
        WIDTH : integer := 16
    );
    port (
        clk      : in  std_logic;
        rst      : in  std_logic;
        data_in  : in  signed(WIDTH-1 downto 0);
        data_out : out signed(WIDTH-1 downto 0)
    );
end fir_filter;

architecture rtl of fir_filter is
    type tap_array is array (0 to TAPS-1) of signed(WIDTH-1 downto 0);
    signal shift_reg : tap_array := (others => (others => '0'));
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                shift_reg <= (others => (others => '0'));
            else
                shift_reg(0) <= data_in;
                for i in 1 to TAPS-1 loop
                    shift_reg(i) <= shift_reg(i-1);
                end loop;
            end if;
        end if;
    end process;
    data_out <= shift_reg(TAPS-1);
end rtl;
