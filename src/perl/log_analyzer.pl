#!/usr/bin/perl
# Phase 559: Perl Log Parsing & Analysis
# 드론 로그 파싱: 정규식 기반 이벤트 추출, 통계 집계, 이상 패턴 탐지

use strict;
use warnings;

# PRNG
package PRNG;
sub new {
    my ($class, $seed) = @_;
    bless { state => ($seed // 42) ^ 0x6c62272e }, $class;
}
sub next {
    my $self = shift;
    $self->{state} ^= ($self->{state} << 13) & 0xFFFFFFFF;
    $self->{state} ^= ($self->{state} >> 7);
    $self->{state} ^= ($self->{state} << 17) & 0xFFFFFFFF;
    return abs($self->{state});
}
sub uniform {
    my $self = shift;
    return ($self->next() % 10000) / 10000.0;
}

# Log entry generator
package LogGenerator;
sub new {
    my ($class, $n_drones, $seed) = @_;
    bless {
        rng => PRNG->new($seed),
        n_drones => $n_drones // 10,
        log_entries => [],
    }, $class;
}

sub generate {
    my ($self, $n_entries) = @_;
    my @levels = qw(INFO WARN ERROR CRITICAL);
    my @events = qw(takeoff landing waypoint_reached battery_low collision_warning
                     geofence_breach comm_lost sensor_error motor_fault link_established);

    for my $i (0 .. $n_entries - 1) {
        my $drone = "drone_" . ($self->{rng}->next() % $self->{n_drones});
        my $level = $levels[$self->{rng}->next() % scalar(@levels)];
        my $event = $events[$self->{rng}->next() % scalar(@events)];
        my $ts = sprintf("2026-03-31T%02d:%02d:%02d",
                         $i % 24, ($i * 7) % 60, ($i * 13) % 60);
        my $value = sprintf("%.2f", $self->{rng}->uniform() * 100);

        my $entry = "[$ts] [$level] $drone: $event value=$value";
        push @{$self->{log_entries}}, $entry;
    }
}

# Log analyzer
package LogAnalyzer;
sub new {
    my ($class) = @_;
    bless {
        total_entries => 0,
        level_counts => {},
        event_counts => {},
        drone_counts => {},
        errors => [],
        anomalies => [],
    }, $class;
}

sub parse_entry {
    my ($self, $line) = @_;
    if ($line =~ /^\[([^\]]+)\]\s+\[(\w+)\]\s+(\w+):\s+(\w+)\s+value=(.+)$/) {
        return {
            timestamp => $1,
            level     => $2,
            drone_id  => $3,
            event     => $4,
            value     => $5 + 0,
        };
    }
    return undef;
}

sub analyze {
    my ($self, $entries) = @_;
    for my $line (@$entries) {
        my $parsed = $self->parse_entry($line);
        next unless $parsed;
        $self->{total_entries}++;

        $self->{level_counts}{$parsed->{level}}++;
        $self->{event_counts}{$parsed->{event}}++;
        $self->{drone_counts}{$parsed->{drone_id}}++;

        if ($parsed->{level} eq 'ERROR' || $parsed->{level} eq 'CRITICAL') {
            push @{$self->{errors}}, $parsed;
        }

        # Anomaly detection: high values
        if ($parsed->{value} > 90) {
            push @{$self->{anomalies}}, $parsed;
        }
    }
}

sub summary {
    my $self = shift;
    my $n_errors = scalar(@{$self->{errors}});
    my $n_anomalies = scalar(@{$self->{anomalies}});
    my $n_drones = scalar(keys %{$self->{drone_counts}});
    return {
        total_entries => $self->{total_entries},
        error_count   => $n_errors,
        anomaly_count => $n_anomalies,
        drones_seen   => $n_drones,
        level_counts  => $self->{level_counts},
    };
}

# Main
package main;
my $gen = LogGenerator->new(10, 42);
$gen->generate(200);

my $analyzer = LogAnalyzer->new();
$analyzer->analyze($gen->{log_entries});

my $summary = $analyzer->summary();
printf("Total entries: %d\n", $summary->{total_entries});
printf("Errors: %d\n", $summary->{error_count});
printf("Anomalies: %d\n", $summary->{anomaly_count});
printf("Drones seen: %d\n", $summary->{drones_seen});
for my $level (sort keys %{$summary->{level_counts}}) {
    printf("  %s: %d\n", $level, $summary->{level_counts}{$level});
}
