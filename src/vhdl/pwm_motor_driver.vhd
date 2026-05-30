-- Phase 572: pwm_motor_driver — VHDL 기반 PWM 모터 드라이버
-- SDACS PWM Motor Driver for Drone ESC Control

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- PWM 신호 생성 entity
entity pwm_motor_driver is
    generic (
        CLK_FREQ_HZ  : integer := 100_000_000;  -- 100 MHz 클록
        PWM_FREQ_HZ  : integer := 50;            -- 50 Hz ESC 주파수
        DUTY_BITS    : integer := 12             -- 12비트 듀티 사이클 해상도
    );
    port (
        clk          : in  std_logic;
        rst_n        : in  std_logic;
        -- 모터 제어 입력 (4채널)
        motor_cmd    : in  std_logic_vector(DUTY_BITS - 1 downto 0);
        motor_sel    : in  std_logic_vector(1 downto 0);
        motor_en     : in  std_logic;
        -- PWM 출력 (4채널)
        pwm_out      : out std_logic_vector(3 downto 0);
        -- 상태
        ready        : out std_logic
    );
end entity pwm_motor_driver;

architecture rtl of pwm_motor_driver is

    -- PWM 카운터 주기: CLK_FREQ / PWM_FREQ
    constant PWM_PERIOD : integer := CLK_FREQ_HZ / PWM_FREQ_HZ;
    constant MAX_DUTY   : integer := 2**DUTY_BITS - 1;

    -- 내부 신호
    signal pwm_counter  : integer range 0 to PWM_PERIOD - 1 := 0;
    signal duty_reg     : integer range 0 to MAX_DUTY;

    -- 모터별 듀티 사이클 레지스터 (4채널)
    type duty_array_t is array(0 to 3) of integer range 0 to MAX_DUTY;
    signal duty_ch      : duty_array_t := (others => 1000);  -- 기본 1000 = 1ms (최소 스로틀)

    -- pwm 출력 내부 신호
    signal pwm_internal : std_logic_vector(3 downto 0) := (others => '0');

begin

    -- PWM 카운터 및 듀티 레지스터 업데이트
    proc_pwm_counter: process(clk, rst_n)
    begin
        if rst_n = '0' then
            pwm_counter <= 0;
            duty_ch     <= (others => 1000);
            pwm_internal <= (others => '0');
        elsif rising_edge(clk) then
            -- 모터 명령 업데이트
            if motor_en = '1' then
                duty_ch(to_integer(unsigned(motor_sel))) <=
                    to_integer(unsigned(motor_cmd));
            end if;

            -- PWM 카운터 증가
            if pwm_counter >= PWM_PERIOD - 1 then
                pwm_counter <= 0;
            else
                pwm_counter <= pwm_counter + 1;
            end if;

            -- 각 채널 PWM 출력 생성 (1000-2000 범위 → 1ms-2ms 펄스)
            for ch in 0 to 3 loop
                if pwm_counter < duty_ch(ch) then
                    pwm_internal(ch) <= '1';
                else
                    pwm_internal(ch) <= '0';
                end if;
            end loop;
        end if;
    end process proc_pwm_counter;

    -- 출력 연결
    pwm_out <= pwm_internal;
    ready   <= '1' when rst_n = '1' else '0';

end architecture rtl;

-- 테스트벤치
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity pwm_motor_driver_tb is
end entity pwm_motor_driver_tb;

architecture sim of pwm_motor_driver_tb is
    signal clk      : std_logic := '0';
    signal rst_n    : std_logic := '0';
    signal cmd      : std_logic_vector(11 downto 0) := (others => '0');
    signal sel      : std_logic_vector(1 downto 0)  := "00";
    signal en       : std_logic := '0';
    signal pwm_out  : std_logic_vector(3 downto 0);
    signal rdy      : std_logic;
begin
    clk   <= not clk after 5 ns;  -- 100 MHz
    rst_n <= '1' after 20 ns;

    UUT: entity work.pwm_motor_driver
        generic map (CLK_FREQ_HZ => 1000, PWM_FREQ_HZ => 50, DUTY_BITS => 12)
        port map (clk => clk, rst_n => rst_n, motor_cmd => cmd,
                  motor_sel => sel, motor_en => en, pwm_out => pwm_out, ready => rdy);

    stim: process
    begin
        wait for 30 ns;
        en <= '1'; sel <= "00"; cmd <= std_logic_vector(to_unsigned(1500, 12));
        wait for 50 ns;
        sel <= "01"; cmd <= std_logic_vector(to_unsigned(1800, 12));
        wait for 100 ns;
        wait;
    end process;
end architecture sim;
