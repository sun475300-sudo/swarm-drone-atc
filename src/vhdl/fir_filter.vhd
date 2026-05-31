-- Phase 656 — FIR Filter (VHDL)
-- 드론 IMU 신호 노이즈 제거용 16탭 FIR 저역통과 필터

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity fir_filter is
    generic (
        DATA_WIDTH : integer := 16;
        TAPS       : integer := 16
    );
    port (
        clk      : in  std_logic;
        reset_n  : in  std_logic;
        data_in  : in  signed(DATA_WIDTH - 1 downto 0);
        data_out : out signed(DATA_WIDTH + 15 downto 0)
    );
end entity fir_filter;

architecture rtl of fir_filter is

    -- Hamming window 계수 (Q15 고정소수점, 정규화된 차단 주파수 0.1)
    type coeff_array is array (0 to TAPS - 1) of signed(DATA_WIDTH - 1 downto 0);
    constant COEFFS : coeff_array := (
        to_signed(  23, DATA_WIDTH),
        to_signed(  75, DATA_WIDTH),
        to_signed( 165, DATA_WIDTH),
        to_signed( 294, DATA_WIDTH),
        to_signed( 451, DATA_WIDTH),
        to_signed( 614, DATA_WIDTH),
        to_signed( 754, DATA_WIDTH),
        to_signed( 840, DATA_WIDTH),
        to_signed( 840, DATA_WIDTH),
        to_signed( 754, DATA_WIDTH),
        to_signed( 614, DATA_WIDTH),
        to_signed( 451, DATA_WIDTH),
        to_signed( 294, DATA_WIDTH),
        to_signed( 165, DATA_WIDTH),
        to_signed(  75, DATA_WIDTH),
        to_signed(  23, DATA_WIDTH)
    );

    type shift_reg_t is array (0 to TAPS - 1) of signed(DATA_WIDTH - 1 downto 0);
    signal shift_reg : shift_reg_t := (others => (others => '0'));
    signal accum     : signed(DATA_WIDTH + 15 downto 0) := (others => '0');

begin

    process(clk, reset_n)
        variable sum : signed(DATA_WIDTH + 15 downto 0);
    begin
        if reset_n = '0' then
            shift_reg <= (others => (others => '0'));
            accum     <= (others => '0');
        elsif rising_edge(clk) then
            -- 시프트 레지스터 갱신
            shift_reg(1 to TAPS - 1) <= shift_reg(0 to TAPS - 2);
            shift_reg(0) <= data_in;

            -- MAC 누산
            sum := (others => '0');
            for i in 0 to TAPS - 1 loop
                sum := sum + resize(shift_reg(i) * COEFFS(i), DATA_WIDTH + 16);
            end loop;
            accum <= sum;
        end if;
    end process;

    data_out <= accum;

end architecture rtl;
