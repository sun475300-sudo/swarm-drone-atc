-- Phase 646: FIR Filter — 드론 센서 신호 FIR 필터 (VHDL)
-- Finite Impulse Response filter for IMU sensor noise suppression.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Entity declaration for the FIR filter
entity FIR_Filter is
    generic (
        DATA_WIDTH : integer := 16;
        COEFF_WIDTH : integer := 16;
        NUM_TAPS : integer := 8   -- Filter order (8-tap FIR)
    );
    port (
        clk     : in  std_logic;
        rst_n   : in  std_logic;
        din     : in  signed(DATA_WIDTH-1 downto 0);
        din_valid : in std_logic;
        dout    : out signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0);
        dout_valid : out std_logic
    );
end entity FIR_Filter;

-- Architecture: Direct form FIR implementation
architecture rtl of FIR_Filter is

    -- Low-pass FIR coefficients (scaled by 2^15)
    type coeff_array is array (0 to NUM_TAPS-1) of signed(COEFF_WIDTH-1 downto 0);
    constant COEFFICIENTS : coeff_array := (
        to_signed(512,  COEFF_WIDTH),
        to_signed(1024, COEFF_WIDTH),
        to_signed(2048, COEFF_WIDTH),
        to_signed(4096, COEFF_WIDTH),
        to_signed(4096, COEFF_WIDTH),
        to_signed(2048, COEFF_WIDTH),
        to_signed(1024, COEFF_WIDTH),
        to_signed(512,  COEFF_WIDTH)
    );

    -- Delay line (shift register)
    type delay_line is array (0 to NUM_TAPS-1) of signed(DATA_WIDTH-1 downto 0);
    signal taps : delay_line := (others => (others => '0'));
    signal accumulator : signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0);
    signal valid_pipe : std_logic := '0';

begin

    -- Shift register and MAC process
    process(clk, rst_n)
        variable acc : signed(DATA_WIDTH+COEFF_WIDTH-1 downto 0);
    begin
        if rst_n = '0' then
            taps <= (others => (others => '0'));
            accumulator <= (others => '0');
            valid_pipe <= '0';
        elsif rising_edge(clk) then
            valid_pipe <= din_valid;
            if din_valid = '1' then
                -- Shift delay line
                for i in NUM_TAPS-1 downto 1 loop
                    taps(i) <= taps(i-1);
                end loop;
                taps(0) <= din;

                -- MAC: multiply-accumulate
                acc := (others => '0');
                for i in 0 to NUM_TAPS-1 loop
                    acc := acc + resize(taps(i) * COEFFICIENTS(i), DATA_WIDTH+COEFF_WIDTH);
                end loop;
                accumulator <= acc;
            end if;
        end if;
    end process;

    dout <= accumulator;
    dout_valid <= valid_pipe;

end architecture rtl;

-- Testbench for FIR_Filter (Phase 646)
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity FIR_Filter_TB is
end entity FIR_Filter_TB;

architecture sim of FIR_Filter_TB is
    constant CLK_PERIOD : time := 10 ns;
    signal clk, rst_n, din_valid, dout_valid : std_logic := '0';
    signal din  : signed(15 downto 0) := (others => '0');
    signal dout : signed(31 downto 0);
begin
    uut : entity work.FIR_Filter
        port map(clk, rst_n, din, din_valid, dout, dout_valid);

    clk_proc : process
    begin
        loop
            clk <= '0'; wait for CLK_PERIOD/2;
            clk <= '1'; wait for CLK_PERIOD/2;
        end loop;
    end process;

    stim_proc : process
    begin
        rst_n <= '0'; wait for 20 ns;
        rst_n <= '1'; din_valid <= '1';
        -- Apply impulse
        din <= to_signed(1000, 16); wait for CLK_PERIOD;
        din <= to_signed(0, 16);
        for i in 0 to 10 loop
            wait for CLK_PERIOD;
        end loop;
        wait;
    end process;
end architecture sim;
