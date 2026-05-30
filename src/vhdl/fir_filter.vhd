-- Phase 656 — VHDL FIR Filter (FPGA digital signal processing)
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter is
    generic (N_TAPS : integer := 8);
    port (
        clk     : in  std_logic;
        rst     : in  std_logic;
        x_in    : in  signed(15 downto 0);
        y_out   : out signed(31 downto 0)
    );
end entity fir_filter;

architecture rtl of fir_filter is
    type tap_array is array (0 to N_TAPS-1) of signed(15 downto 0);
    type coeff_array is array (0 to N_TAPS-1) of signed(15 downto 0);
    signal taps : tap_array := (others => (others => '0'));
    constant coeffs : coeff_array := (
        x"0100", x"0200", x"0400", x"0800",
        x"0800", x"0400", x"0200", x"0100"
    );
begin
    process(clk, rst) is
        variable acc : signed(31 downto 0);
    begin
        if rst = '1' then
            taps <= (others => (others => '0'));
            y_out <= (others => '0');
        elsif rising_edge(clk) then
            taps(1 to N_TAPS-1) <= taps(0 to N_TAPS-2);
            taps(0) <= x_in;
            acc := (others => '0');
            for i in 0 to N_TAPS-1 loop
                acc := acc + taps(i) * coeffs(i);
            end loop;
            y_out <= acc;
        end if;
    end process;
end architecture rtl;
