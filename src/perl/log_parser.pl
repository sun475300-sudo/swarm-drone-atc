#!/usr/bin/perl
# Phase 618: log_parser — Perl 기반 군집 드론 로그 파서
# SDACS Log Parser — Advanced regex 기반 로그 분석

use strict;
use warnings;
use POSIX qw(strftime);

# 로그 파서 클래스
package LogParser;

sub new {
    my ($class, %opts) = @_;
    return bless {
        patterns => $opts{patterns} || {},
        results  => [],
        errors   => [],
    }, $class;
}

# 정규식 패턴 등록
sub register_pattern {
    my ($self, $name, $regex, $extractor) = @_;
    $self->{patterns}{$name} = { regex => $regex, extractor => $extractor };
}

# 단일 라인 파싱 (regex 매칭)
sub parse_line {
    my ($self, $line) = @_;
    chomp $line;
    for my $name (keys %{$self->{patterns}}) {
        my $pat  = $self->{patterns}{$name};
        my $re   = $pat->{regex};
        if ($line =~ $re) {
            my $entry = $pat->{extractor}->($line);
            $entry->{_type}   = $name;
            $entry->{_raw}    = $line;
            return $entry;
        }
    }
    return undef;
}

# 여러 라인 파싱
sub parse_lines {
    my ($self, @lines) = @_;
    my @results;
    for my $line (@lines) {
        my $entry = $self->parse_line($line);
        if (defined $entry) {
            push @results, $entry;
            push @{$self->{results}}, $entry;
        }
    }
    return @results;
}

# 결과 필터링
sub filter_by_type {
    my ($self, $type) = @_;
    return grep { $_->{_type} eq $type } @{$self->{results}};
}

# 통계 집계
sub aggregate_stats {
    my ($self) = @_;
    my %stats;
    for my $entry (@{$self->{results}}) {
        my $did = $entry->{drone_id} // 'unknown';
        $stats{$did}{count}++;
        if (defined $entry->{battery}) {
            push @{$stats{$did}{batteries}}, $entry->{battery};
        }
        if (defined $entry->{altitude}) {
            push @{$stats{$did}{altitudes}}, $entry->{altitude};
        }
    }
    return %stats;
}

package main;

# SDACS 표준 로그 파서 인스턴스 생성
my $parser = LogParser->new();

# 텔레메트리 로그 패턴 등록 (regex 기반)
$parser->register_pattern(
    'telemetry',
    qr/^\[(\d{4}-\d{2}-\d{2}T[\d:]+)\]\s+DRONE_(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([\d.]+)\s+bat=([\d.]+)/,
    sub {
        my $line = shift;
        my ($ts, $id, $lat, $lon, $alt, $bat) =
            $line =~ /^\[(\S+)\]\s+DRONE_(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([\d.]+)\s+bat=([\d.]+)/;
        return {
            timestamp => $ts, drone_id => $id + 0,
            lat => $lat + 0.0, lon => $lon + 0.0,
            altitude => $alt + 0.0, battery => $bat + 0.0,
        };
    }
);

# 이벤트 로그 패턴 등록 (regex 기반)
$parser->register_pattern(
    'event',
    qr/^\[(\S+)\]\s+EVENT\s+(\w+)\s+drone=(\d+)/,
    sub {
        my $line = shift;
        my ($ts, $event, $did) =
            $line =~ /^\[(\S+)\]\s+EVENT\s+(\w+)\s+drone=(\d+)/;
        my %params;
        while ($line =~ /(\w+)=([\d.]+)/g) {
            $params{$1} = $2 + 0.0 unless $1 eq 'drone';
        }
        return { timestamp => $ts, event => $event, drone_id => $did + 0, params => \%params };
    }
);

# 오류 로그 패턴 등록 (regex 기반)
$parser->register_pattern(
    'error',
    qr/^\[(\S+)\]\s+ERROR\s+drone=(\d+)\s+(.+)$/,
    sub {
        my $line = shift;
        my ($ts, $did, $msg) =
            $line =~ /^\[(\S+)\]\s+ERROR\s+drone=(\d+)\s+(.+)$/;
        return { timestamp => $ts, drone_id => $did + 0, message => $msg };
    }
);

# 테스트 로그 데이터 파싱
my @log_lines = (
    "[2026-05-30T04:00:01] DRONE_0 lat=37.500 lon=127.000 alt=50.0 bat=95.0",
    "[2026-05-30T04:00:01] DRONE_1 lat=37.501 lon=127.001 alt=52.0 bat=88.0",
    "[2026-05-30T04:00:02] DRONE_0 lat=37.502 lon=127.002 alt=51.5 bat=94.5",
    "[2026-05-30T04:00:02] EVENT CONFLICT drone=0 separation=3.8 other=1",
    "[2026-05-30T04:00:03] ERROR drone=1 GPS_FIX_LOST quality=0.1",
    "[2026-05-30T04:00:04] DRONE_1 lat=37.503 lon=127.003 alt=53.0 bat=87.5",
);

print "SDACS Log Parser — Phase 618\n";
my @entries = $parser->parse_lines(@log_lines);
printf "파싱 완료: %d 항목\n", scalar @entries;

my %stats = $parser->aggregate_stats();
for my $did (sort { $a <=> $b } keys %stats) {
    my $s = $stats{$did};
    my @bats = @{$s->{batteries} // []};
    my $avg_bat = @bats ? (do { my $sum = 0; $sum += $_ for @bats; $sum / @bats }) : 'N/A';
    printf "Drone %d: %d 샘플, 평균 배터리=%.1f%%\n",
        $did, $s->{count}, ref($avg_bat) ? 0 : $avg_bat;
}
