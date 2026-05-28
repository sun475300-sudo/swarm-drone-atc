-- Phase 656: FIR Filter — VHDL Digital Signal Processing
-- FIR (Finite Impulse Response) 디지털 필터 FPGA 구현

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
        clk       : in  std_logic;
        rst       : in  std_logic;
        data_in   : in  signed(DATA_WIDTH-1 downto 0);
        data_valid: in  std_logic;
        data_out  : out signed(DATA_WIDTH-1 downto 0);
        out_valid : out std_logic
    );
end fir_filter;

architecture behavioral of fir_filter is

    type coeff_array is array (0 to N_TAPS-1) of signed(COEFF_WIDTH-1 downto 0);
    type delay_line  is array (0 to N_TAPS-1) of signed(DATA_WIDTH-1 downto 0);

    -- Low-pass filter coefficients (Hamming window, normalized)
    constant COEFFS : coeff_array := (
        to_signed(512,  COEFF_WIDTH),  -- h[0]
        to_signed(1024, COEFF_WIDTH),  -- h[1]
        to_signed(2048, COEFF_WIDTH),  -- h[2]
        to_signed(4096, COEFF_WIDTH),  -- h[3]  center
        to_signed(4096, COEFF_WIDTH),  -- h[4]
        to_signed(2048, COEFF_WIDTH),  -- h[5]
        to_signed(1024, COEFF_WIDTH),  -- h[6]
        to_signed(512,  COEFF_WIDTH)   -- h[7]
    );

    signal delay : delay_line := (others => (others => '0'));
    signal accumulator : signed(DATA_WIDTH + COEFF_WIDTH + 3 downto 0);
    signal computing   : std_logic := '0';
    signal tap_idx     : integer range 0 to N_TAPS := 0;
    signal result_reg  : signed(DATA_WIDTH-1 downto 0) := (others => '0');
    signal valid_reg   : std_logic := '0';

begin

    process(clk)
        variable product : signed(DATA_WIDTH + COEFF_WIDTH - 1 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '1' then
                delay       <= (others => (others => '0'));
                accumulator <= (others => '0');
                computing   <= '0';
                tap_idx     <= 0;
                result_reg  <= (others => '0');
                valid_reg   <= '0';

            elsif data_valid = '1' and computing = '0' then
                -- Shift delay line
                for i in N_TAPS-1 downto 1 loop
                    delay(i) <= delay(i-1);
                end loop;
                delay(0) <= data_in;

                -- Start MAC computation
                accumulator <= (others => '0');
                computing   <= '1';
                tap_idx     <= 0;
                valid_reg   <= '0';

            elsif computing = '1' then
                if tap_idx < N_TAPS then
                    product := delay(tap_idx) * COEFFS(tap_idx);
                    accumulator <= accumulator + resize(product, accumulator'length);
                    tap_idx <= tap_idx + 1;
                else
                    -- Output: truncate to DATA_WIDTH
                    result_reg <= accumulator(DATA_WIDTH + COEFF_WIDTH - 2 downto COEFF_WIDTH - 1);
                    valid_reg  <= '1';
                    computing  <= '0';
                end if;
            else
                valid_reg <= '0';
            end if;
        end if;
    end process;

    data_out  <= result_reg;
    out_valid <= valid_reg;

end behavioral;

-- Testbench
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter_tb is
end fir_filter_tb;

architecture sim of fir_filter_tb is
    signal clk, rst, din_valid, dout_valid : std_logic := '0';
    signal data_in, data_out : signed(15 downto 0) := (others => '0');
    constant CLK_PERIOD : time := 10 ns;
begin

    uut: entity work.fir_filter
        generic map (DATA_WIDTH => 16, COEFF_WIDTH => 16, N_TAPS => 8)
        port map (clk => clk, rst => rst, data_in => data_in,
                  data_valid => din_valid, data_out => data_out,
                  out_valid => dout_valid);

    clk_proc: process
    begin
        clk <= '0'; wait for CLK_PERIOD / 2;
        clk <= '1'; wait for CLK_PERIOD / 2;
    end process;

    stim: process
    begin
        rst <= '1';
        wait for CLK_PERIOD * 3;
        rst <= '0';
        wait for CLK_PERIOD;

        -- Feed impulse
        data_in <= to_signed(1000, 16);
        din_valid <= '1';
        wait for CLK_PERIOD;
        din_valid <= '0';
        wait for CLK_PERIOD * 12;

        -- Feed step
        for i in 0 to 15 loop
            data_in <= to_signed(2000, 16);
            din_valid <= '1';
            wait for CLK_PERIOD;
            din_valid <= '0';
            wait for CLK_PERIOD * 12;
        end loop;

        wait for CLK_PERIOD * 20;
        assert false report "FIR Filter TB Complete" severity note;
        wait;
    end process;

end sim;
