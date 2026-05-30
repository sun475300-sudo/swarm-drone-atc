#!/usr/bin/perl
# SDACS Log Parser — Perl (Phase 618)
# 드론 군집 시스템 로그 파서 (regex 기반)

use strict;
use warnings;
use POSIX qw(strftime);

# 로그 레벨 상수
use constant {
    LEVEL_DEBUG => 10,
    LEVEL_INFO  => 20,
    LEVEL_WARN  => 30,
    LEVEL_ERROR => 40,
    LEVEL_CRIT  => 50,
};

my %LEVEL_MAP = (
    DEBUG    => LEVEL_DEBUG,
    INFO     => LEVEL_INFO,
    WARNING  => LEVEL_WARN,
    WARN     => LEVEL_WARN,
    ERROR    => LEVEL_ERROR,
    CRITICAL => LEVEL_CRIT,
);

# 로그 파서 클래스
package LogParser;

sub new {
    my ($class, %opts) = @_;
    return bless {
        min_level   => $opts{min_level} // 'INFO',
        entries     => [],
        drone_stats => {},
        error_count => 0,
        warn_count  => 0,
    }, $class;
}

# 단일 로그 라인 파싱 (regex 활용, Phase 618)
sub parse_line {
    my ($self, $line) = @_;
    chomp $line;

    # 패턴 1: [YYYY-MM-DD HH:MM:SS] LEVEL DRONE_ID: message
    if ($line =~ /^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]\s+(\w+)\s+(\S+?):\s+(.+)$/) {
        return $self->_build_entry($1, $2, $3, $4);
    }

    # 패턴 2: YYYY-MM-DDTHH:MM:SSZ level drone_id message
    if ($line =~ /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?)\s+(\w+)\s+(\S+)\s+(.+)$/) {
        return $self->_build_entry($1, $2, $3, $4);
    }

    return undef;
}

sub _build_entry {
    my ($self, $ts, $level, $drone_id, $msg) = @_;
    my $entry = {
        timestamp => $ts,
        level     => uc($level),
        drone_id  => $drone_id,
        message   => $msg,
    };

    push @{$self->{entries}}, $entry;
    $self->{drone_stats}{$drone_id}{count}++;
    $self->{error_count}++ if $entry->{level} eq 'ERROR' || $entry->{level} eq 'CRITICAL';
    $self->{warn_count}++  if $entry->{level} eq 'WARN' || $entry->{level} eq 'WARNING';

    # 키워드 추출 (conflict, battery, altitude)
    if ($msg =~ /conflict/i)  { $entry->{tags} = ['conflict'] }
    if ($msg =~ /battery/i)   { push @{$entry->{tags}}, 'battery' }
    if ($msg =~ /altitude/i)  { push @{$entry->{tags}}, 'altitude' }

    return $entry;
}

sub parse_text {
    my ($self, $text) = @_;
    my @lines = split /\n/, $text;
    my @parsed = map { $self->parse_line($_) } @lines;
    return grep { defined } @parsed;
}

sub filter_by_level {
    my ($self, $level) = @_;
    return grep { $_->{level} eq uc($level) } @{$self->{entries}};
}

sub filter_by_drone {
    my ($self, $drone_id) = @_;
    return grep { $_->{drone_id} eq $drone_id } @{$self->{entries}};
}

sub summary {
    my ($self) = @_;
    return {
        total_entries => scalar @{$self->{entries}},
        error_count   => $self->{error_count},
        warn_count    => $self->{warn_count},
        unique_drones => scalar keys %{$self->{drone_stats}},
    };
}

sub entry_count { scalar @{$_[0]->{entries}} }

package main;

if (!caller()) {
    my $parser = LogParser->new(min_level => 'INFO');
    my $sample = join "\n", (
        "[2026-05-30 23:00:00] INFO  D-001: Takeoff sequence initiated at altitude 0m",
        "[2026-05-30 23:01:30] WARN  D-002: battery level dropping to 18%",
        "[2026-05-30 23:02:45] ERROR D-001: conflict detected with D-003 distance=28.3m",
        "[2026-05-30 23:03:00] INFO  D-003: altitude adjustment to 110m",
    );

    my @entries = $parser->parse_text($sample);
    my $s = $parser->summary();
    printf "Parsed: %d entries | Errors: %d | Warnings: %d | Drones: %d\n",
        $s->{total_entries}, $s->{error_count}, $s->{warn_count}, $s->{unique_drones};
}

1;
