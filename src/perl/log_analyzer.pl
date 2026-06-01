#!/usr/bin/perl
# Phase 559: Log Analyzer — 드론 비행 로그 분석기 (Perl)
# Regex-based log parser and analyzer for swarm drone telemetry logs.

use strict;
use warnings;
use POSIX qw(strftime);

our $VERSION = '1.0.0';
our $PHASE   = 559;

# ── Log entry regex patterns ─────────────────────────────────────

my $LOG_PATTERN  = qr/^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]\s+(\w+)\s+drone_(\d+)\s+(.*)/;
my $TELEM_PATTERN = qr/pos=\(([-\d.]+),([-\d.]+),([-\d.]+)\)\s+bat=([\d.]+)/;
my $ERR_PATTERN  = qr/(ERROR|WARN|CRITICAL):\s+(.*)/;
my $CONFLICT_PATTERN = qr/conflict_detected\s+between\s+drone_(\d+)\s+and\s+drone_(\d+)/;

# ── Log Analyzer class ────────────────────────────────────────────

package LogAnalyzer;

sub new {
    my ($class, %opts) = @_;
    return bless {
        entries    => [],
        errors     => [],
        conflicts  => [],
        drone_stats => {},
        phase      => $PHASE,
    }, $class;
}

# parse() ingests a block of log text and extracts entries.
sub parse {
    my ($self, $text) = @_;
    my @lines = split /\n/, $text;
    for my $line (@lines) {
        next unless $line =~ $LOG_PATTERN;
        my ($ts, $level, $drone_id, $msg) = ($1, $2, $3, $4);
        my $entry = {ts => $ts, level => $level, drone_id => $drone_id, msg => $msg};
        push @{$self->{entries}}, $entry;

        # Extract telemetry via regex
        if ($msg =~ $TELEM_PATTERN) {
            $self->{drone_stats}{$drone_id} //= {count => 0, battery_sum => 0};
            $self->{drone_stats}{$drone_id}{count}++;
            $self->{drone_stats}{$drone_id}{battery_sum} += $4;
        }

        # Capture errors
        if ($msg =~ $ERR_PATTERN) {
            push @{$self->{errors}}, {drone_id => $drone_id, severity => $1, detail => $2};
        }

        # Detect conflicts
        if ($msg =~ $CONFLICT_PATTERN) {
            push @{$self->{conflicts}}, {d1 => $1, d2 => $2, ts => $ts};
        }
    }
    return scalar @lines;
}

# generate_report() produces a summary string.
sub generate_report {
    my ($self) = @_;
    my $n_drones   = scalar keys %{$self->{drone_stats}};
    my $n_entries  = scalar @{$self->{entries}};
    my $n_errors   = scalar @{$self->{errors}};
    my $n_conflicts = scalar @{$self->{conflicts}};

    my $report = sprintf(
        "=== Log Analysis Report (Phase %d) ===\n" .
        "Total entries:   %d\n" .
        "Active drones:   %d\n" .
        "Errors/Warnings: %d\n" .
        "Conflicts:       %d\n",
        $self->{phase}, $n_entries, $n_drones, $n_errors, $n_conflicts
    );

    # Per-drone battery averages
    for my $did (sort keys %{$self->{drone_stats}}) {
        my $st  = $self->{drone_stats}{$did};
        my $avg = $st->{count} > 0 ? $st->{battery_sum} / $st->{count} : 0;
        $report .= sprintf("  drone_%s avg_battery=%.1f%%\n", $did, $avg);
    }
    return $report;
}

# summarize() returns a hash with key statistics.
sub summarize {
    my ($self) = @_;
    return {
        total_entries => scalar @{$self->{entries}},
        error_count   => scalar @{$self->{errors}},
        conflict_count => scalar @{$self->{conflicts}},
        drone_count   => scalar keys %{$self->{drone_stats}},
    };
}

package main;

# ── Synthetic log generator ────────────────────────────────────────

sub generate_logs {
    my ($n_drones, $n_steps) = @_;
    my @lines;
    for my $t (1..$n_steps) {
        for my $d (1..$n_drones) {
            my $bat = 100 - $t * 0.5;
            my $ts  = sprintf("2024-01-%02dT%02d:%02d:%02d", 1, 0, 0, $t % 60);
            push @lines, sprintf("[%s] INFO drone_%d pos=(%.1f,%.1f,50.0) bat=%.1f",
                                 $ts, $d, $t*1.0, $t*0.5, $bat);
            if ($t % 10 == 0 && $bat < 50) {
                push @lines, sprintf("[%s] WARN drone_%d ERROR: low battery %.1f%%", $ts, $d, $bat);
            }
        }
    }
    return join("\n", @lines);
}

# ── Entry point ────────────────────────────────────────────────────

my $analyzer = LogAnalyzer->new();
my $log_text = generate_logs(5, 30);
my $n_parsed = $analyzer->parse($log_text);
my $report   = $analyzer->generate_report();
my $summary  = $analyzer->summarize();

printf("Phase %d: Log Analyzer — 드론 로그 분석기\n", $PHASE);
printf("Parsed %d lines\n", $n_parsed);
print $report;
printf("Summary: entries=%d errors=%d\n",
       $summary->{total_entries}, $summary->{error_count});
