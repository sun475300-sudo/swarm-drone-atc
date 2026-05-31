-- Phase 656 — FIR Digital Filter (FPGA) in VHDL
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter is
    generic (TAPS : integer := 8; WIDTH : integer := 16);
    port (
        clk     : in  std_logic;
        rst     : in  std_logic;
        data_in : in  signed(WIDTH-1 downto 0);
        data_out: out signed(WIDTH+integer(log2(real(TAPS)))-1 downto 0)
    );
end fir_filter;

architecture rtl of fir_filter is
    type coeff_array is array(0 to TAPS-1) of signed(WIDTH-1 downto 0);
    type delay_line  is array(0 to TAPS-1) of signed(WIDTH-1 downto 0);
    -- Symmetric low-pass coefficients (fixed-point Q15)
    constant COEFFS : coeff_array := (
        x"0100",x"0200",x"0400",x"0800",x"0800",x"0400",x"0200",x"0100");
    signal delay : delay_line := (others => (others => '0'));
    signal acc   : signed(WIDTH+3 downto 0) := (others => '0');
begin
    process(clk) begin
        if rising_edge(clk) then
            if rst = '1' then
                delay <= (others => (others => '0')); acc <= (others => '0');
            else
                delay <= data_in & delay(0 to TAPS-2);
                acc <= (others => '0');
                for i in 0 to TAPS-1 loop
                    acc <= acc + resize(delay(i) * COEFFS(i), acc'length);
                end loop;
            end if;
        end if;
    end process;
    data_out <= acc;
end rtl;
