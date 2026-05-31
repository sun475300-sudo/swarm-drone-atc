-- pwm_motor_driver.vhd - PWM Motor Driver for drone motors
-- SDACS swarm drone airspace control system

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

-- Entity declaration for PWM motor driver
entity pwm_motor_driver is
    generic (
        CLK_FREQ    : integer := 100_000_000;  -- 100 MHz clock
        PWM_FREQ    : integer := 400;           -- 400 Hz PWM for motors
        RESOLUTION  : integer := 16             -- 16-bit PWM resolution
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        enable      : in  std_logic;
        duty_cycle  : in  std_logic_vector(15 downto 0);  -- pwm duty cycle input
        motor_pwm   : out std_logic;
        fault       : out std_logic
    );
end entity pwm_motor_driver;

-- Architecture for PWM generation
architecture rtl of pwm_motor_driver is
    constant PWM_PERIOD : integer := CLK_FREQ / PWM_FREQ;
    signal counter      : unsigned(31 downto 0) := (others => '0');
    signal threshold    : unsigned(31 downto 0) := (others => '0');
    signal pwm_out      : std_logic := '0';
    signal fault_reg    : std_logic := '0';

    -- Internal drone motor state signals
    type motor_state_t is (IDLE, SPINNING, FAULT_STATE, STOPPING);
    signal motor_state : motor_state_t := IDLE;

begin

    -- PWM counter process
    process(clk, rst)
    begin
        if rst = '1' then
            counter     <= (others => '0');
            pwm_out     <= '0';
            fault_reg   <= '0';
            motor_state <= IDLE;
        elsif rising_edge(clk) then
            threshold <= resize(unsigned(duty_cycle) * to_unsigned(PWM_PERIOD, 32) / 65535, 32);

            if counter >= to_unsigned(PWM_PERIOD - 1, 32) then
                counter <= (others => '0');
            else
                counter <= counter + 1;
            end if;

            -- PWM output generation
            if enable = '1' then
                if counter < threshold then
                    pwm_out <= '1';
                else
                    pwm_out <= '0';
                end if;
                motor_state <= SPINNING;
            else
                pwm_out     <= '0';
                motor_state <= IDLE;
            end if;

            -- Fault detection: duty cycle > 95%
            if unsigned(duty_cycle) > 62259 then
                fault_reg   <= '1';
                motor_state <= FAULT_STATE;
            else
                fault_reg   <= '0';
            end if;
        end if;
    end process;

    motor_pwm <= pwm_out;
    fault     <= fault_reg;

end architecture rtl;
