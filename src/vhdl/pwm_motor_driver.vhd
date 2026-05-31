-- Phase 572 — PWM motor driver entity in VHDL
-- SDACS swarm drone ESC control via configurable PWM generation.
-- Generates a PWM signal whose duty cycle is set by an 8-bit
-- throttle input.  Period is fixed at 20 ms (50 Hz standard RC).

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

-- ---------------------------------------------------------------
-- entity pwm_motor_driver
-- Ports:
--   clk      : system clock (assumed 50 MHz)
--   rst_n    : active-low synchronous reset
--   throttle : 8-bit duty cycle command (0=0%, 255=100%)
--   pwm_out  : PWM output signal to ESC
--   fault    : asserted when throttle exceeds safe threshold
-- ---------------------------------------------------------------
entity pwm_motor_driver is
    generic (
        CLK_FREQ_HZ  : integer := 50_000_000;   -- 50 MHz system clock
        PWM_FREQ_HZ  : integer := 50;            -- 50 Hz PWM period
        SAFE_MAX     : integer := 200             -- throttle safety ceiling
    );
    port (
        clk      : in  std_logic;
        rst_n    : in  std_logic;
        throttle : in  std_logic_vector(7 downto 0);
        pwm_out  : out std_logic;
        fault    : out std_logic
    );
end entity pwm_motor_driver;

-- ---------------------------------------------------------------
-- architecture rtl of pwm_motor_driver
-- ---------------------------------------------------------------
architecture rtl of pwm_motor_driver is

    -- Number of clock ticks per complete pwm period
    constant PERIOD_TICKS : integer := CLK_FREQ_HZ / PWM_FREQ_HZ;

    -- Number of clock ticks corresponding to full-scale throttle
    constant FULL_SCALE   : integer := PERIOD_TICKS;

    signal counter        : integer range 0 to PERIOD_TICKS - 1 := 0;
    signal duty_ticks     : integer range 0 to PERIOD_TICKS - 1 := 0;
    signal throttle_int   : integer range 0 to 255 := 0;
    signal pwm_reg        : std_logic := '0';
    signal fault_reg      : std_logic := '0';

begin

    -- Convert throttle vector to integer once per cycle
    throttle_int <= to_integer(unsigned(throttle));

    -- Duty cycle scaling: duty_ticks = throttle * PERIOD_TICKS / 255
    duty_ticks <= (throttle_int * PERIOD_TICKS) / 255;

    -- Fault detection: throttle above safe maximum
    fault_reg <= '1' when throttle_int > SAFE_MAX else '0';

    -- PWM counter and output generation
    pwm_proc : process(clk)
    begin
        if rising_edge(clk) then
            if rst_n = '0' then
                counter  <= 0;
                pwm_reg  <= '0';
            else
                if counter < PERIOD_TICKS - 1 then
                    counter <= counter + 1;
                else
                    counter <= 0;
                end if;

                -- Assert pwm high during the duty window
                if counter < duty_ticks then
                    pwm_reg <= '1';
                else
                    pwm_reg <= '0';
                end if;
            end if;
        end if;
    end process pwm_proc;

    -- Drive output ports
    pwm_out <= pwm_reg;
    fault   <= fault_reg;

end architecture rtl;
