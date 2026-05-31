-- P572: PWM Motor Driver - VHDL PWM generation for brushless motors
-- Phase 572: Variable-frequency PWM for quadcopter motor control

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity pwm_motor_driver is
    generic (
        CLK_FREQ_HZ    : integer := 50_000_000;  -- 50 MHz clock
        PWM_FREQ_HZ    : integer := 400;          -- 400 Hz PWM
        RESOLUTION_BITS: integer := 16
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        -- Motor control inputs (0..65535 = 0..100% duty)
        motor1_duty : in  unsigned(RESOLUTION_BITS-1 downto 0);
        motor2_duty : in  unsigned(RESOLUTION_BITS-1 downto 0);
        motor3_duty : in  unsigned(RESOLUTION_BITS-1 downto 0);
        motor4_duty : in  unsigned(RESOLUTION_BITS-1 downto 0);
        -- PWM outputs
        pwm_out     : out std_logic_vector(3 downto 0);
        -- Status
        armed       : in  std_logic;
        fault       : out std_logic
    );
end pwm_motor_driver;

architecture behavioral of pwm_motor_driver is
    constant PWM_PERIOD : integer := CLK_FREQ_HZ / PWM_FREQ_HZ;

    signal counter : unsigned(RESOLUTION_BITS-1 downto 0);
    signal period_cnt : integer range 0 to PWM_PERIOD-1;
    signal scaled_duty : unsigned(RESOLUTION_BITS-1 downto 0);

    -- Safety: min/max duty cycle limits
    constant DUTY_MIN : unsigned(RESOLUTION_BITS-1 downto 0) := to_unsigned(6553, RESOLUTION_BITS);  -- 10%
    constant DUTY_MAX : unsigned(RESOLUTION_BITS-1 downto 0) := to_unsigned(58981, RESOLUTION_BITS); -- 90%

    -- Clamp duty cycle to safe range
    function clamp_duty(d: unsigned) return unsigned is
    begin
        if d < DUTY_MIN then return DUTY_MIN;
        elsif d > DUTY_MAX then return DUTY_MAX;
        else return d;
        end if;
    end function;

begin
    -- PWM counter
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                counter   <= (others => '0');
                period_cnt <= 0;
                fault      <= '0';
            else
                if period_cnt >= PWM_PERIOD - 1 then
                    period_cnt <= 0;
                    counter    <= (others => '0');
                else
                    period_cnt <= period_cnt + 1;
                    counter    <= counter + 1;
                end if;
            end if;
        end if;
    end process;

    -- PWM comparator output
    process(counter, motor1_duty, motor2_duty, motor3_duty, motor4_duty, armed)
        variable d1, d2, d3, d4 : unsigned(RESOLUTION_BITS-1 downto 0);
    begin
        if armed = '1' then
            d1 := clamp_duty(motor1_duty);
            d2 := clamp_duty(motor2_duty);
            d3 := clamp_duty(motor3_duty);
            d4 := clamp_duty(motor4_duty);
            pwm_out(0) <= '1' when counter < d1 else '0';
            pwm_out(1) <= '1' when counter < d2 else '0';
            pwm_out(2) <= '1' when counter < d3 else '0';
            pwm_out(3) <= '1' when counter < d4 else '0';
        else
            pwm_out <= "0000";
        end if;
    end process;

end behavioral;
