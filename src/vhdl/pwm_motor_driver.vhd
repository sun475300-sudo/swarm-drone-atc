-- Phase 572: PWM Motor Driver — VHDL
-- 드론 BLDC 모터 PWM 신호 생성.
-- 4채널 독립 듀티 사이클 제어.

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

-- ─── PWM 생성기 엔티티 ───
entity pwm_generator is
    generic (
        CLK_FREQ    : integer := 100_000_000;  -- 100 MHz
        PWM_FREQ    : integer := 50_000;       -- 50 kHz
        RESOLUTION  : integer := 8             -- 8비트 해상도 (256단계)
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        duty_cycle  : in  std_logic_vector(RESOLUTION-1 downto 0);
        pwm_out     : out std_logic
    );
end entity pwm_generator;

architecture rtl of pwm_generator is
    constant PERIOD   : integer := CLK_FREQ / PWM_FREQ;
    constant STEP     : integer := PERIOD / (2**RESOLUTION);
    signal counter    : unsigned(15 downto 0) := (others => '0');
    signal duty_val   : unsigned(RESOLUTION-1 downto 0);
    signal threshold  : unsigned(15 downto 0);
begin
    duty_val  <= unsigned(duty_cycle);
    threshold <= resize(duty_val * to_unsigned(STEP, 8), 16);

    process(clk, rst)
    begin
        if rst = '1' then
            counter <= (others => '0');
            pwm_out <= '0';
        elsif rising_edge(clk) then
            if counter >= to_unsigned(PERIOD - 1, 16) then
                counter <= (others => '0');
            else
                counter <= counter + 1;
            end if;

            if counter < threshold then
                pwm_out <= '1';
            else
                pwm_out <= '0';
            end if;
        end if;
    end process;
end architecture rtl;

-- ─── 4채널 모터 드라이버 ───
entity quad_motor_driver is
    generic (
        CLK_FREQ   : integer := 100_000_000;
        PWM_FREQ   : integer := 50_000;
        RESOLUTION : integer := 8
    );
    port (
        clk        : in  std_logic;
        rst        : in  std_logic;
        -- 4개 모터 듀티 사이클
        duty_m1    : in  std_logic_vector(RESOLUTION-1 downto 0);
        duty_m2    : in  std_logic_vector(RESOLUTION-1 downto 0);
        duty_m3    : in  std_logic_vector(RESOLUTION-1 downto 0);
        duty_m4    : in  std_logic_vector(RESOLUTION-1 downto 0);
        -- PWM 출력
        pwm_m1     : out std_logic;
        pwm_m2     : out std_logic;
        pwm_m3     : out std_logic;
        pwm_m4     : out std_logic;
        -- 상태
        armed      : in  std_logic;
        fault      : out std_logic
    );
end entity quad_motor_driver;

architecture structural of quad_motor_driver is
    signal pwm_raw : std_logic_vector(3 downto 0);
    signal fault_detect : std_logic := '0';
begin
    -- 4개 PWM 생성기 인스턴스
    GEN_M1: entity work.pwm_generator
        generic map (CLK_FREQ, PWM_FREQ, RESOLUTION)
        port map (clk, rst, duty_m1, pwm_raw(0));

    GEN_M2: entity work.pwm_generator
        generic map (CLK_FREQ, PWM_FREQ, RESOLUTION)
        port map (clk, rst, duty_m2, pwm_raw(1));

    GEN_M3: entity work.pwm_generator
        generic map (CLK_FREQ, PWM_FREQ, RESOLUTION)
        port map (clk, rst, duty_m3, pwm_raw(2));

    GEN_M4: entity work.pwm_generator
        generic map (CLK_FREQ, PWM_FREQ, RESOLUTION)
        port map (clk, rst, duty_m4, pwm_raw(3));

    -- Armed 게이트: 무장 해제 시 모든 PWM 차단
    pwm_m1 <= pwm_raw(0) and armed;
    pwm_m2 <= pwm_raw(1) and armed;
    pwm_m3 <= pwm_raw(2) and armed;
    pwm_m4 <= pwm_raw(3) and armed;

    -- 간이 결함 감지: 모든 듀티가 최대이면 과부하 경고
    process(clk)
    begin
        if rising_edge(clk) then
            if duty_m1 = (duty_m1'range => '1') and
               duty_m2 = (duty_m2'range => '1') and
               duty_m3 = (duty_m3'range => '1') and
               duty_m4 = (duty_m4'range => '1') then
                fault_detect <= '1';
            else
                fault_detect <= '0';
            end if;
        end if;
    end process;

    fault <= fault_detect;
end architecture structural;
