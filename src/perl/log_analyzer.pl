#!/usr/bin/perl
# log_analyzer.pl - Log Analyzer for SDACS drone system (Phase 559)
# Perl implementation with regex-based log parsing and statistical analysis

use strict;
use warnings;
use POSIX qw(strftime);

package LogAnalyzer;

sub new {
    my ($class, %args) = @_;
    return bless {
        log_file   => $args{log_file} || '',
        entries    => [],
        stats      => {},
        patterns   => {
            timestamp => qr/(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})/,
            level     => qr/\[(ERROR|WARN|INFO|DEBUG|CRITICAL)\]/,
            drone_id  => qr/drone=(\S+)/,
            metric    => qr/(\w+)=([\d.]+)/,
        },
    }, $class;
}

sub parse_line {
    my ($self, $line) = @_;
    chomp $line;
    my %entry;

    # Extract timestamp using regex =~
    if ($line =~ $self->{patterns}{timestamp}) {
        $entry{timestamp} = $1;
    }

    # Extract log level
    if ($line =~ $self->{patterns}{level}) {
        $entry{level} = $1;
    }

    # Extract drone ID
    if ($line =~ $self->{patterns}{drone_id}) {
        $entry{drone_id} = $1;
    }

    # Extract all key=value metrics
    my %metrics;
    while ($line =~ /(\w+)=([\d.]+)/g) {
        $metrics{$1} = $2;
    }
    $entry{metrics} = \%metrics if %metrics;
    $entry{raw} = $line;

    return \%entry if %entry;
    return undef;
}

sub analyze_file {
    my ($self, $file) = @_;
    $file ||= $self->{log_file};
    open(my $fh, '<', $file) or die "Cannot open $file: $!";
    while (my $line = <$fh>) {
        my $entry = $self->parse_line($line);
        push @{$self->{entries}}, $entry if $entry;
    }
    close $fh;
    return scalar @{$self->{entries}};
}

sub analyze_stream {
    my ($self, $lines_ref) = @_;
    for my $line (@$lines_ref) {
        my $entry = $self->parse_line($line);
        push @{$self->{entries}}, $entry if $entry;
    }
}

sub compute_statistics {
    my ($self) = @_;
    my %level_counts;
    my %drone_counts;
    my %metric_sums;
    my %metric_counts;

    for my $entry (@{$self->{entries}}) {
        $level_counts{$entry->{level}}++   if $entry->{level};
        $drone_counts{$entry->{drone_id}}++ if $entry->{drone_id};

        if ($entry->{metrics}) {
            for my $key (keys %{$entry->{metrics}}) {
                $metric_sums{$key}   += $entry->{metrics}{$key};
                $metric_counts{$key}++;
            }
        }
    }

    my %averages;
    for my $key (keys %metric_sums) {
        $averages{$key} = $metric_sums{$key} / $metric_counts{$key}
            if $metric_counts{$key} > 0;
    }

    $self->{stats} = {
        total_entries  => scalar @{$self->{entries}},
        level_counts   => \%level_counts,
        drone_counts   => \%drone_counts,
        metric_averages => \%averages,
    };

    return $self->{stats};
}

sub report {
    my ($self) = @_;
    my $stats = $self->compute_statistics();
    my $report = "=== SDACS Log Analyzer Report (Phase 559) ===\n";
    $report .= "Total entries: $stats->{total_entries}\n";
    for my $level (sort keys %{$stats->{level_counts}}) {
        $report .= sprintf("  %-8s: %d\n", $level, $stats->{level_counts}{$level});
    }
    return $report;
}

package main;

my $analyzer = LogAnalyzer->new();
my @sample_lines = (
    "[INFO] 2026-01-01T10:00:00 drone=D-001 altitude=50.5 battery=85",
    "[WARN] 2026-01-01T10:00:01 drone=D-002 battery=15 altitude=45.2",
    "[ERROR] 2026-01-01T10:00:02 drone=D-003 collision_risk=0.8",
    "[DEBUG] 2026-01-01T10:00:03 drone=D-001 speed=12.3",
);

$analyzer->analyze_stream(\@sample_lines);
print $analyzer->report();
