#!/usr/bin/perl
# Phase 559: log_analyzer — Perl 기반 군집 드론 로그 분석기
# SDACS Log Analyzer — regex 기반 텔레메트리 로그 파싱

use strict;
use warnings;
use POSIX qw(strftime);
use List::Util qw(min max sum);

# 로그 파일 분석기 클래스 (Perl OO)
package Analyzer;

sub new {
    my ($class, %opts) = @_;
    return bless {
        log_file    => $opts{log_file} // '',
        entries     => [],
        errors      => [],
        stats       => {},
        regex_cache => {},
    }, $class;
}

# 텔레메트리 로그 라인 파싱 (regex 기반)
# 형식: [TIMESTAMP] DRONE_ID lat=XX.XX lon=YY.YY alt=ZZ.Z bat=BB.B%
sub parse_line {
    my ($self, $line) = @_;
    chomp $line;

    # 타임스탬프 + 드론 ID + 텔레메트리 파싱 regex
    if ($line =~ /^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]\s+DRONE_(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([\d.]+)\s+bat=([\d.]+)%?/) {
        return {
            timestamp => $1,
            drone_id  => int($2),
            lat       => $3 + 0.0,
            lon       => $4 + 0.0,
            alt       => $5 + 0.0,
            battery   => $6 + 0.0,
            type      => 'telemetry',
        };
    }
    # 이벤트 로그 파싱 regex
    elsif ($line =~ /^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]\s+EVENT\s+(\w+)\s+drone=(\d+)\s+(.+)$/) {
        my ($ts, $event, $did, $detail) = ($1, $2, $3, $4);
        my %params;
        while ($detail =~ /(\w+)=([\d.]+)/g) {
            $params{$1} = $2 + 0.0;
        }
        return {
            timestamp => $ts,
            drone_id  => int($did),
            event     => $event,
            params    => \%params,
            type      => 'event',
        };
    }
    # 오류 로그 파싱 regex
    elsif ($line =~ /^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]\s+ERROR\s+drone=(\d+)\s+(.+)$/) {
        return {
            timestamp => $1,
            drone_id  => int($2),
            message   => $3,
            type      => 'error',
        };
    }
    return undef;
}

# 로그 파일 읽기 및 파싱
sub parse_file {
    my ($self, $filename) = @_;
    $filename //= $self->{log_file};
    open(my $fh, '<', $filename) or die "Cannot open $filename: $!";
    while (my $line = <$fh>) {
        my $entry = $self->parse_line($line);
        if (defined $entry) {
            push @{$self->{entries}}, $entry;
            push @{$self->{errors}}, $entry if $entry->{type} eq 'error';
        }
    }
    close $fh;
    return scalar @{$self->{entries}};
}

# 텔레메트리 통계 계산
sub compute_stats {
    my ($self) = @_;
    my %by_drone;
    for my $entry (@{$self->{entries}}) {
        next unless $entry->{type} eq 'telemetry';
        my $did = $entry->{drone_id};
        push @{$by_drone{$did}{battery}},  $entry->{battery};
        push @{$by_drone{$did}{altitude}}, $entry->{alt};
    }
    for my $did (sort { $a <=> $b } keys %by_drone) {
        my @bats = @{$by_drone{$did}{battery}};
        my @alts = @{$by_drone{$did}{altitude}};
        $self->{stats}{$did} = {
            battery_mean => (sum(@bats) / @bats),
            battery_min  => min(@bats),
            altitude_mean => (sum(@alts) / @alts),
            altitude_max  => max(@alts),
            sample_count  => scalar @bats,
        };
    }
    return $self->{stats};
}

# 보고서 출력
sub report {
    my ($self) = @_;
    printf "=== SDACS Log Analyzer 보고서 (Phase 559) ===\n";
    printf "총 로그 항목: %d\n", scalar @{$self->{entries}};
    printf "오류 항목:    %d\n", scalar @{$self->{errors}};
    my $stats = $self->compute_stats();
    for my $did (sort { $a <=> $b } keys %$stats) {
        my $s = $stats->{$did};
        printf "Drone %2d: battery avg=%.1f%% min=%.1f%% | alt avg=%.1fm max=%.1fm [%d samples]\n",
            $did, $s->{battery_mean}, $s->{battery_min},
            $s->{altitude_mean}, $s->{altitude_max}, $s->{sample_count};
    }
}

package main;

# 테스트 데이터 생성 및 분석
my $analyzer = Analyzer->new();

# 인라인 로그 파싱 데모
my @test_lines = (
    "[2026-05-30T04:00:01] DRONE_0 lat=37.500 lon=127.000 alt=50.0 bat=95.0%",
    "[2026-05-30T04:00:01] DRONE_1 lat=37.501 lon=127.001 alt=52.0 bat=88.0%",
    "[2026-05-30T04:00:02] DRONE_0 lat=37.501 lon=127.001 alt=51.0 bat=94.5%",
    "[2026-05-30T04:00:02] EVENT CONFLICT drone=0 separation=3.2 other=1",
    "[2026-05-30T04:00:03] ERROR drone=1 GPS_FIX_LOST signal_quality=0.1",
    "[2026-05-30T04:00:03] DRONE_0 lat=37.502 lon=127.002 alt=55.0 bat=94.0%",
    "[2026-05-30T04:00:04] DRONE_1 lat=37.503 lon=127.003 alt=53.0 bat=87.5%",
);

print "SDACS Log Analyzer — Phase 559\n";
for my $line (@test_lines) {
    my $entry = $analyzer->parse_line($line);
    if (defined $entry) {
        push @{$analyzer->{entries}}, $entry;
        push @{$analyzer->{errors}}, $entry if $entry->{type} eq 'error';
    }
}
$analyzer->report();
