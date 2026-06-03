#!/usr/bin/perl
# Phase 559: Log Analyzer — Perl
# SDACS intelligent log parsing and Analyzer for drone flight logs

use strict;
use warnings;
use POSIX qw(strftime);
use File::Basename;
use Scalar::Util qw(looks_like_number);

# Phase 559 marker — parse, Analyzer with regex pattern matching

package SDACS::LogAnalyzer;

# Log level constants
use constant {
    LOG_DEBUG    => 0,
    LOG_INFO     => 1,
    LOG_WARNING  => 2,
    LOG_ERROR    => 3,
    LOG_CRITICAL => 4,
};

my %LEVEL_NAMES = (
    0 => 'DEBUG',
    1 => 'INFO',
    2 => 'WARNING',
    3 => 'ERROR',
    4 => 'CRITICAL',
);

# Log entry regex patterns
my %PATTERNS = (
    timestamp  => qr/(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)/,
    level      => qr/\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]/i,
    drone_id   => qr/drone[_\s]?(?:id)?[=:\s]+["']?([A-Za-z0-9_-]+)["']?/i,
    battery    => qr/battery[_\s]?(?:pct|percent|level)?[=:\s]+(\d+(?:\.\d+)?)/i,
    altitude   => qr/alt(?:itude)?[=:\s]+(\d+(?:\.\d+)?)/i,
    speed      => qr/speed[=:\s]+(\d+(?:\.\d+)?)/i,
    conflict   => qr/conflict|separation\s+violation|collision\s+risk/i,
    rtl        => qr/RTL|return[_\s]to[_\s]launch/i,
    error_code => qr/ERR[_-]?(\d{3,4})/,
);

sub new {
    my ($class, %opts) = @_;
    return bless {
        min_level  => $opts{min_level}  // LOG_INFO,
        max_entries => $opts{max_entries} // 100_000,
        entries    => [],
        stats      => {
            total     => 0,
            by_level  => {map { $_ => 0 } 0..4},
            by_drone  => {},
            conflicts => 0,
            rtl_events => 0,
            errors    => [],
        },
    }, $class;
}

# Parse a single log line
sub parse_line {
    my ($self, $line) = @_;
    chomp $line;
    return undef unless length $line;

    my %entry = (raw => $line);

    # Extract timestamp
    if ($line =~ $PATTERNS{timestamp}) {
        $entry{timestamp} = $1;
    }

    # Extract log level
    if ($line =~ $PATTERNS{level}) {
        my $lvl_str = uc($1);
        my %level_map = (DEBUG=>0, INFO=>1, WARNING=>2, ERROR=>3, CRITICAL=>4);
        $entry{level} = $level_map{$lvl_str} // 1;
        $entry{level_name} = $lvl_str;
    }

    return undef if defined $entry{level} && $entry{level} < $self->{min_level};

    # Extract drone ID
    if ($line =~ $PATTERNS{drone_id}) {
        $entry{drone_id} = $1;
    }

    # Extract numeric telemetry values via regex
    if ($line =~ $PATTERNS{battery}) {
        $entry{battery} = $1 + 0;
    }
    if ($line =~ $PATTERNS{altitude}) {
        $entry{altitude} = $1 + 0;
    }
    if ($line =~ $PATTERNS{speed}) {
        $entry{speed} = $1 + 0;
    }

    # Flag special events
    $entry{is_conflict} = ($line =~ $PATTERNS{conflict}) ? 1 : 0;
    $entry{is_rtl}      = ($line =~ $PATTERNS{rtl})      ? 1 : 0;

    # Error code
    if ($line =~ $PATTERNS{error_code}) {
        $entry{error_code} = "ERR-$1";
    }

    return \%entry;
}

# Ingest a single log line
sub ingest {
    my ($self, $line) = @_;
    my $entry = $self->parse_line($line);
    return unless defined $entry;

    push @{$self->{entries}}, $entry;
    if (@{$self->{entries}} > $self->{max_entries}) {
        shift @{$self->{entries}};
    }

    $self->_update_stats($entry);
    return $entry;
}

# Parse a log file
sub parse_file {
    my ($self, $filename) = @_;
    open my $fh, '<', $filename
        or die "Cannot open log file '$filename': $!";
    my $count = 0;
    while (my $line = <$fh>) {
        $self->ingest($line);
        $count++;
    }
    close $fh;
    return $count;
}

# Parse log from a string (for testing)
sub parse_string {
    my ($self, $text) = @_;
    my $count = 0;
    for my $line (split /\n/, $text) {
        $self->ingest($line);
        $count++;
    }
    return $count;
}

sub _update_stats {
    my ($self, $entry) = @_;
    my $stats = $self->{stats};
    $stats->{total}++;
    my $lvl = $entry->{level} // 1;
    $stats->{by_level}{$lvl}++;
    if ($entry->{drone_id}) {
        $stats->{by_drone}{$entry->{drone_id}}++;
    }
    $stats->{conflicts}++ if $entry->{is_conflict};
    $stats->{rtl_events}++ if $entry->{is_rtl};
    if ($lvl >= LOG_ERROR) {
        push @{$stats->{errors}}, $entry;
        shift @{$stats->{errors}} if @{$stats->{errors}} > 100;
    }
}

# Filter entries by predicate
sub filter {
    my ($self, $pred) = @_;
    return grep { $pred->($_) } @{$self->{entries}};
}

# Get entries for a specific drone
sub drone_entries {
    my ($self, $drone_id) = @_;
    return $self->filter(sub { ($_[0]->{drone_id} // '') eq $drone_id });
}

# Battery alerts: entries with battery below threshold
sub battery_alerts {
    my ($self, $threshold) = @_;
    $threshold //= 20;
    return $self->filter(sub {
        defined $_[0]->{battery} && $_[0]->{battery} < $threshold
    });
}

# Get summary report
sub summary {
    my $self = shift;
    my $s = $self->{stats};
    return {
        total_lines  => $s->{total},
        conflicts    => $s->{conflicts},
        rtl_events   => $s->{rtl_events},
        error_count  => $s->{by_level}{3} + $s->{by_level}{4},
        drones_seen  => scalar keys %{$s->{by_drone}},
        by_level     => {map { $LEVEL_NAMES{$_} => $s->{by_level}{$_} } keys %LEVEL_NAMES},
    };
}

# Generate human-readable report
sub report {
    my $self = shift;
    my $sum = $self->summary();
    my @lines = (
        "=== SDACS Log Analyzer Report ===",
        sprintf("Total log lines: %d", $sum->{total_lines}),
        sprintf("Drones detected: %d", $sum->{drones_seen}),
        sprintf("Conflicts:       %d", $sum->{conflicts}),
        sprintf("RTL events:      %d", $sum->{rtl_events}),
        sprintf("Errors:          %d", $sum->{error_count}),
        "Level breakdown:",
        map { sprintf("  %-10s: %d", $_, $sum->{by_level}{$_}) } sort keys %{$sum->{by_level}},
    );
    return join("\n", @lines);
}

package main;

# Demo
my $analyzer = SDACS::LogAnalyzer->new(min_level => SDACS::LogAnalyzer::LOG_INFO);

my $sample_log = <<'LOGDATA';
2026-06-01T10:00:01Z [INFO] drone_id=D001 altitude=60.0 speed=10.0 battery=85.5
2026-06-01T10:00:02Z [WARNING] drone_id=D002 battery=19.5 RTL triggered
2026-06-01T10:00:03Z [ERROR] drone_id=D001 ERR-1042 separation violation conflict detected
2026-06-01T10:00:04Z [INFO] drone_id=D003 altitude=65.0 speed=8.5 battery=72.0
2026-06-01T10:00:05Z [CRITICAL] drone_id=D002 battery=8.0 emergency landing
LOGDATA

$analyzer->parse_string($sample_log);
print $analyzer->report() . "\n";

my $sum = $analyzer->summary();
printf "Phase 559: Parsed %d lines, found %d conflicts\n",
    $sum->{total_lines}, $sum->{conflicts};
