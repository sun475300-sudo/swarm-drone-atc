-- SDACS FIR Filter — VHDL
-- 군집드론 FIR 필터 구현

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity fir_filter is
    generic (
        DATA_WIDTH  : integer := 16;
        COEFF_WIDTH : integer := 16;
        NUM_TAPS    : integer := 8
    );
    port (
        clk      : in  std_logic;
        rst      : in  std_logic;
        data_in  : in  std_logic_vector(DATA_WIDTH-1 downto 0);
        valid_in : in  std_logic;
        data_out : out std_logic_vector(DATA_WIDTH-1 downto 0);
        valid_out: out std_logic
    );
end entity fir_filter;

architecture rtl of fir_filter is
    type coeff_array is array(0 to NUM_TAPS-1) of integer;
    type delay_line  is array(0 to NUM_TAPS-1) of signed(DATA_WIDTH-1 downto 0);

    constant coeffs : coeff_array := (1, 2, 4, 8, 8, 4, 2, 1);
    signal delay : delay_line := (others => (others => '0'));
    signal valid_reg : std_logic := '0';

begin
    process(clk)
        variable acc : integer := 0;
    begin
        if rising_edge(clk) then
            if rst = '1' then
                delay     <= (others => (others => '0'));
                data_out  <= (others => '0');
                valid_out <= '0';
                valid_reg <= '0';
            elsif valid_in = '1' then
                -- 시프트 레지스터 업데이트
                for i in NUM_TAPS-1 downto 1 loop
                    delay(i) <= delay(i-1);
                end loop;
                delay(0) <= signed(data_in);

                -- MAC 연산
                acc := 0;
                for i in 0 to NUM_TAPS-1 loop
                    acc := acc + to_integer(delay(i)) * coeffs(i);
                end loop;
                data_out  <= std_logic_vector(to_signed(acc / 30, DATA_WIDTH));
                valid_out <= '1';
            else
                valid_out <= '0';
            end if;
        end if;
    end process;
end architecture rtl;
