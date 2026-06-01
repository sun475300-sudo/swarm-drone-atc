-- PWM Motor Driver — VHDL for SDACS propulsion control
-- Phase 572

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity pwm_motor_driver is
    generic (
        CLK_FREQ_HZ  : integer := 50_000_000;
        PWM_FREQ_HZ  : integer := 50;
        RESOLUTION   : integer := 16
    );
    port (
        clk      : in  std_logic;
        rst_n    : in  std_logic;
        enable   : in  std_logic;
        duty     : in  unsigned(RESOLUTION-1 downto 0);
        pwm_out  : out std_logic;
        fault    : out std_logic
    );
end pwm_motor_driver;

architecture rtl of pwm_motor_driver is
    constant PERIOD_TICKS : integer := CLK_FREQ_HZ / PWM_FREQ_HZ;
    signal counter   : integer range 0 to PERIOD_TICKS-1 := 0;
    signal threshold : integer range 0 to PERIOD_TICKS-1 := 0;
    signal pwm_reg   : std_logic := '0';
    signal fault_reg : std_logic := '0';

begin
    -- Duty cycle to threshold conversion
    threshold <= to_integer(duty) * PERIOD_TICKS / (2**RESOLUTION);

    -- PWM generation process
    pwm_proc: process(clk, rst_n)
    begin
        if rst_n = '0' then
            counter  <= 0;
            pwm_reg  <= '0';
            fault_reg <= '0';
        elsif rising_edge(clk) then
            if enable = '0' then
                pwm_reg <= '0';
                counter <= 0;
            else
                -- Fault detection: duty > 95%
                if to_integer(duty) > (2**RESOLUTION - 2**RESOLUTION/20) then
                    fault_reg <= '1';
                    pwm_reg   <= '0';
                else
                    fault_reg <= '0';
                    if counter < threshold then
                        pwm_reg <= '1';
                    else
                        pwm_reg <= '0';
                    end if;
                    if counter = PERIOD_TICKS - 1 then
                        counter <= 0;
                    else
                        counter <= counter + 1;
                    end if;
                end if;
            end if;
        end if;
    end process pwm_proc;

    pwm_out <= pwm_reg;
    fault   <= fault_reg;

end rtl;
