-- PWM Motor Driver — SDACS Phase 572
-- Controls drone motor speed via PWM signal
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity pwm is
    generic (
        CLK_FREQ   : integer := 100_000_000;  -- 100 MHz
        PWM_FREQ   : integer := 50;           -- 50 Hz
        RESOLUTION : integer := 16            -- 16-bit
    );
    port (
        clk      : in  std_logic;
        rst      : in  std_logic;
        duty     : in  unsigned(15 downto 0);
        pwm_out  : out std_logic;
        fault    : out std_logic
    );
end entity pwm;

architecture behavioral of pwm is
    constant PERIOD : integer := CLK_FREQ / PWM_FREQ;
    signal counter  : integer range 0 to PERIOD - 1 := 0;
    signal thresh   : integer := 0;
begin
    process(clk, rst)
    begin
        if rst = '1' then
            counter  <= 0;
            pwm_out  <= '0';
            fault    <= '0';
        elsif rising_edge(clk) then
            thresh  <= to_integer(duty) * PERIOD / 65535;
            if counter < thresh then
                pwm_out <= '1';
            else
                pwm_out <= '0';
            end if;
            if counter = PERIOD - 1 then
                counter <= 0;
            else
                counter <= counter + 1;
            end if;
        end if;
    end process;
    fault <= '0';
end architecture behavioral;
-- end
-- end
-- end
