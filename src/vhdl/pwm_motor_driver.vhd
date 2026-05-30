-- SDACS PWM Motor Driver — VHDL
-- Controls drone motor speed via PWM signal

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity pwm_motor_driver is
    generic (
        CLK_FREQ    : integer := 50000000;  -- 50 MHz clock
        PWM_FREQ    : integer := 50;         -- 50 Hz PWM frequency
        RESOLUTION  : integer := 16          -- 16-bit resolution
    );
    port (
        clk         : in  std_logic;
        rst_n       : in  std_logic;
        duty_cycle  : in  std_logic_vector(15 downto 0);
        motor_en    : in  std_logic;
        pwm_out     : out std_logic;
        fault_n     : out std_logic
    );
end entity pwm_motor_driver;

architecture rtl of pwm_motor_driver is

    constant PWM_PERIOD : integer := CLK_FREQ / PWM_FREQ;

    signal counter      : unsigned(31 downto 0) := (others => '0');
    signal duty_reg     : unsigned(15 downto 0) := (others => '0');
    signal threshold    : unsigned(31 downto 0) := (others => '0');
    signal pwm_reg      : std_logic := '0';
    signal fault_reg    : std_logic := '1';
    signal sync_duty    : std_logic_vector(15 downto 0) := (others => '0');

begin

    -- Synchronise duty cycle input
    process(clk, rst_n)
    begin
        if rst_n = '0' then
            sync_duty <= (others => '0');
            duty_reg  <= (others => '0');
        elsif rising_edge(clk) then
            sync_duty <= duty_cycle;
            duty_reg  <= unsigned(sync_duty);
        end if;
    end process;

    -- Compute threshold from duty cycle
    process(clk, rst_n)
    begin
        if rst_n = '0' then
            threshold <= (others => '0');
        elsif rising_edge(clk) then
            threshold <= resize(duty_reg * to_unsigned(PWM_PERIOD, 16) / 65535, 32);
        end if;
    end process;

    -- PWM counter and output generation
    process(clk, rst_n)
    begin
        if rst_n = '0' then
            counter  <= (others => '0');
            pwm_reg  <= '0';
            fault_reg <= '1';
        elsif rising_edge(clk) then
            if motor_en = '0' then
                pwm_reg  <= '0';
                counter  <= (others => '0');
                fault_reg <= '1';
            else
                if counter >= to_unsigned(PWM_PERIOD - 1, 32) then
                    counter <= (others => '0');
                else
                    counter <= counter + 1;
                end if;

                if counter < threshold then
                    pwm_reg <= '1';
                else
                    pwm_reg <= '0';
                end if;

                fault_reg <= '1';
            end if;
        end if;
    end process;

    pwm_out <= pwm_reg;
    fault_n <= fault_reg;

end architecture rtl;
