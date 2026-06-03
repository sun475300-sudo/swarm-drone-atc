-- Phase 572: PWM Motor Driver — VHDL Implementation
-- SDACS PWM controller for drone motor speed regulation

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity pwm_motor_driver is
    generic (
        CLK_FREQ    : integer := 50_000_000;
        PWM_FREQ    : integer := 400;
        RESOLUTION  : integer := 16
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        duty_cycle  : in  std_logic_vector(RESOLUTION-1 downto 0);
        pwm_out     : out std_logic;
        fault       : out std_logic
    );
end entity pwm_motor_driver;

architecture rtl of pwm_motor_driver is
    constant PWM_PERIOD : integer := CLK_FREQ / PWM_FREQ;
    signal counter      : unsigned(23 downto 0) := (others => '0');
    signal duty_reg     : unsigned(RESOLUTION-1 downto 0) := (others => '0');
    signal threshold    : unsigned(23 downto 0) := (others => '0');
    signal pwm_reg      : std_logic := '0';
    signal fault_reg    : std_logic := '0';
begin

    -- PWM generation process
    pwm_proc : process(clk, rst)
    begin
        if rst = '1' then
            counter     <= (others => '0');
            duty_reg    <= (others => '0');
            threshold   <= (others => '0');
            pwm_reg     <= '0';
            fault_reg   <= '0';
        elsif rising_edge(clk) then
            -- Latch duty cycle at start of period
            if counter = 0 then
                duty_reg  <= unsigned(duty_cycle);
                threshold <= resize(unsigned(duty_cycle) * to_unsigned(PWM_PERIOD, 24)
                             / to_unsigned(2**RESOLUTION, 24), 24);
            end if;

            -- PWM compare
            if counter < threshold then
                pwm_reg <= '1';
            else
                pwm_reg <= '0';
            end if;

            -- Counter wrap
            if counter >= to_unsigned(PWM_PERIOD - 1, 24) then
                counter <= (others => '0');
            else
                counter <= counter + 1;
            end if;

            -- Fault detection: duty > 100%
            if unsigned(duty_cycle) = (2**RESOLUTION - 1) then
                fault_reg <= '1';
            else
                fault_reg <= '0';
            end if;
        end if;
    end process pwm_proc;

    pwm_out <= pwm_reg;
    fault   <= fault_reg;

end architecture rtl;
