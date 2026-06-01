-- Phase 572: PWM Motor Driver — 드론 모터 PWM 제어 (VHDL)
-- Pulse Width Modulation driver for brushless drone motor control.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Entity: PWM Motor Driver
entity pwm_motor_driver is
    generic (
        CLK_FREQ  : integer := 50_000_000;  -- 50 MHz system clock
        PWM_FREQ  : integer := 50;           -- 50 Hz PWM (standard servo)
        RESOLUTION: integer := 16            -- duty cycle resolution bits
    );
    port (
        clk       : in  std_logic;
        rst_n     : in  std_logic;
        enable    : in  std_logic;
        -- Thrust command: 0 = min, 2^RESOLUTION-1 = max
        thrust_cmd : in  unsigned(RESOLUTION-1 downto 0);
        pwm_out   : out std_logic;
        -- Status outputs
        period_tick : out std_logic;
        duty_pct   : out unsigned(7 downto 0)  -- 0-100%
    );
end entity pwm_motor_driver;

-- Architecture: behavioral PWM generator
architecture rtl of pwm_motor_driver is
    constant PERIOD_CYCLES : integer := CLK_FREQ / PWM_FREQ;
    constant MAX_DUTY      : integer := 2**RESOLUTION - 1;

    signal counter     : unsigned(23 downto 0) := (others => '0');
    signal duty_cycles : unsigned(23 downto 0) := (others => '0');
    signal pwm_reg     : std_logic := '0';
    signal tick_reg    : std_logic := '0';
begin

    -- PWM generation process
    pwm_proc : process(clk, rst_n)
    begin
        if rst_n = '0' then
            counter    <= (others => '0');
            duty_cycles <= (others => '0');
            pwm_reg    <= '0';
            tick_reg   <= '0';
        elsif rising_edge(clk) then
            tick_reg <= '0';

            if enable = '1' then
                -- Compute duty cycle in clock ticks
                -- duty = (thrust / MAX_DUTY) * PERIOD_CYCLES
                duty_cycles <= resize(
                    (resize(thrust_cmd, 32) * to_unsigned(PERIOD_CYCLES, 32)) / to_unsigned(MAX_DUTY, 32),
                    24);

                if counter < duty_cycles then
                    pwm_reg <= '1';
                else
                    pwm_reg <= '0';
                end if;

                if counter >= to_unsigned(PERIOD_CYCLES - 1, 24) then
                    counter  <= (others => '0');
                    tick_reg <= '1';  -- period complete pulse
                else
                    counter <= counter + 1;
                end if;
            else
                pwm_reg <= '0';
                counter <= (others => '0');
            end if;
        end if;
    end process;

    -- Output assignments
    pwm_out      <= pwm_reg;
    period_tick  <= tick_reg;
    duty_pct     <= resize(
        (resize(thrust_cmd, 16) * to_unsigned(100, 16)) / to_unsigned(MAX_DUTY, 16),
        8);

end architecture rtl;

-- Quad motor controller: four PWM channels for X-frame drone
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity quad_motor_controller is
    port (
        clk         : in  std_logic;
        rst_n       : in  std_logic;
        enable      : in  std_logic;
        thrust_fl   : in  unsigned(15 downto 0);  -- front-left
        thrust_fr   : in  unsigned(15 downto 0);  -- front-right
        thrust_rl   : in  unsigned(15 downto 0);  -- rear-left
        thrust_rr   : in  unsigned(15 downto 0);  -- rear-right
        pwm_fl      : out std_logic;
        pwm_fr      : out std_logic;
        pwm_rl      : out std_logic;
        pwm_rr      : out std_logic
    );
end entity quad_motor_controller;

architecture rtl of quad_motor_controller is
begin
    motor_fl : entity work.pwm_motor_driver
        port map(clk, rst_n, enable, thrust_fl, pwm_fl, open, open);
    motor_fr : entity work.pwm_motor_driver
        port map(clk, rst_n, enable, thrust_fr, pwm_fr, open, open);
    motor_rl : entity work.pwm_motor_driver
        port map(clk, rst_n, enable, thrust_rl, pwm_rl, open, open);
    motor_rr : entity work.pwm_motor_driver
        port map(clk, rst_n, enable, thrust_rr, pwm_rr, open, open);
end architecture rtl;
