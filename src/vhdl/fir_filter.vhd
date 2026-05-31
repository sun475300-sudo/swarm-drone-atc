-- P656: FIR Filter - VHDL stub
-- Finite Impulse Response filter for drone sensor signal processing

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter is
    generic (
        DATA_WIDTH  : integer := 16;
        COEFF_WIDTH : integer := 16;
        N_TAPS      : integer := 8
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        data_in     : in  signed(DATA_WIDTH-1 downto 0);
        data_valid  : in  std_logic;
        data_out    : out signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0);
        output_valid: out std_logic
    );
end fir_filter;

architecture behavioral of fir_filter is
    type coeff_array is array (0 to N_TAPS-1) of signed(COEFF_WIDTH-1 downto 0);
    type delay_array  is array (0 to N_TAPS-1) of signed(DATA_WIDTH-1 downto 0);

    -- Low-pass coefficients (normalized)
    constant COEFFS : coeff_array := (
        to_signed(128,  COEFF_WIDTH),
        to_signed(256,  COEFF_WIDTH),
        to_signed(512,  COEFF_WIDTH),
        to_signed(1024, COEFF_WIDTH),
        to_signed(1024, COEFF_WIDTH),
        to_signed(512,  COEFF_WIDTH),
        to_signed(256,  COEFF_WIDTH),
        to_signed(128,  COEFF_WIDTH)
    );

    signal delay_line : delay_array := (others => (others => '0'));
    signal accumulator : signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0);

begin
    process(clk)
        variable acc : signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '1' then
                delay_line   <= (others => (others => '0'));
                data_out     <= (others => '0');
                output_valid <= '0';
            elsif data_valid = '1' then
                delay_line(0) <= data_in;
                for i in 1 to N_TAPS-1 loop
                    delay_line(i) <= delay_line(i-1);
                end loop;
                acc := (others => '0');
                for i in 0 to N_TAPS-1 loop
                    acc := acc + delay_line(i) * COEFFS(i);
                end loop;
                data_out     <= acc;
                output_valid <= '1';
            else
                output_valid <= '0';
            end if;
        end if;
    end process;
end behavioral;
