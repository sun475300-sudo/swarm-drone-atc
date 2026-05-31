-- fir_filter.vhd - FIR filter for drone sensor signal processing
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter is
    generic (
        DATA_WIDTH   : integer := 16;
        COEFF_WIDTH  : integer := 16;
        NUM_TAPS     : integer := 8
    );
    port (
        clk      : in  std_logic;
        rst      : in  std_logic;
        data_in  : in  std_logic_vector(DATA_WIDTH-1 downto 0);
        valid_in : in  std_logic;
        data_out : out std_logic_vector(DATA_WIDTH-1 downto 0);
        valid_out: out std_logic
    );
end entity fir_filter;

architecture rtl of fir_filter is
    type sample_array is array (0 to NUM_TAPS-1) of signed(DATA_WIDTH-1 downto 0);
    type coeff_array  is array (0 to NUM_TAPS-1) of signed(COEFF_WIDTH-1 downto 0);

    signal delay_line : sample_array := (others => (others => '0'));
    signal coeffs     : coeff_array  := (
        to_signed(128, COEFF_WIDTH), to_signed(256, COEFF_WIDTH),
        to_signed(512, COEFF_WIDTH), to_signed(1024, COEFF_WIDTH),
        to_signed(1024, COEFF_WIDTH), to_signed(512, COEFF_WIDTH),
        to_signed(256, COEFF_WIDTH), to_signed(128, COEFF_WIDTH)
    );
    signal acc        : signed(DATA_WIDTH + COEFF_WIDTH + 3 downto 0) := (others => '0');
    signal valid_pipe : std_logic := '0';

begin
    process(clk, rst)
        variable sum : signed(DATA_WIDTH + COEFF_WIDTH + 3 downto 0);
    begin
        if rst = '1' then
            delay_line <= (others => (others => '0'));
            valid_pipe <= '0';
        elsif rising_edge(clk) then
            valid_pipe <= valid_in;
            if valid_in = '1' then
                for i in NUM_TAPS-1 downto 1 loop
                    delay_line(i) <= delay_line(i-1);
                end loop;
                delay_line(0) <= signed(data_in);

                sum := (others => '0');
                for i in 0 to NUM_TAPS-1 loop
                    sum := sum + resize(delay_line(i) * coeffs(i), sum'length);
                end loop;
                acc <= sum;
            end if;
        end if;
    end process;

    data_out  <= std_logic_vector(acc(DATA_WIDTH + COEFF_WIDTH - 2 downto COEFF_WIDTH - 1));
    valid_out <= valid_pipe;

end architecture rtl;
