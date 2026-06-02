-- Phase 646: FIR Filter — VHDL
-- SDACS Finite Impulse Response filter for drone sensor signal conditioning

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter is
    generic (
        DATA_WIDTH  : integer := 16;
        COEFF_WIDTH : integer := 16;
        NUM_TAPS    : integer := 8
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        data_in     : in  std_logic_vector(DATA_WIDTH-1 downto 0);
        data_valid  : in  std_logic;
        data_out    : out std_logic_vector(DATA_WIDTH+COEFF_WIDTH-1 downto 0);
        out_valid   : out std_logic
    );
end entity fir_filter;

architecture rtl of fir_filter is
    type delay_line_t is array(0 to NUM_TAPS-1) of signed(DATA_WIDTH-1 downto 0);
    type coeff_t      is array(0 to NUM_TAPS-1) of signed(COEFF_WIDTH-1 downto 0);

    -- Low-pass FIR coefficients (symmetric, windowed-sinc)
    constant COEFFS : coeff_t := (
        to_signed(  64, COEFF_WIDTH),
        to_signed( 256, COEFF_WIDTH),
        to_signed( 512, COEFF_WIDTH),
        to_signed( 896, COEFF_WIDTH),
        to_signed( 896, COEFF_WIDTH),
        to_signed( 512, COEFF_WIDTH),
        to_signed( 256, COEFF_WIDTH),
        to_signed(  64, COEFF_WIDTH)
    );

    signal delay_line : delay_line_t := (others => (others => '0'));
    signal acc        : signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0) := (others => '0');
    signal valid_reg  : std_logic := '0';

begin

    fir_proc : process(clk, rst)
        variable sum : signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0);
    begin
        if rst = '1' then
            delay_line <= (others => (others => '0'));
            acc        <= (others => '0');
            valid_reg  <= '0';
        elsif rising_edge(clk) then
            valid_reg <= data_valid;
            if data_valid = '1' then
                -- Shift delay line
                for i in NUM_TAPS-1 downto 1 loop
                    delay_line(i) <= delay_line(i-1);
                end loop;
                delay_line(0) <= signed(data_in);

                -- Compute convolution sum
                sum := (others => '0');
                for i in 0 to NUM_TAPS-1 loop
                    sum := sum + delay_line(i) * COEFFS(i);
                end loop;
                acc <= sum;
            end if;
        end if;
    end process fir_proc;

    data_out  <= std_logic_vector(acc);
    out_valid <= valid_reg;

end architecture rtl;
