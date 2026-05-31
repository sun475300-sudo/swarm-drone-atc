#!/usr/bin/perl
# Phase 559: Log Analyzer for SDACS Drone Operations
# Real-time log parsing with regex pattern matching
# SDACS Log Intelligence Module

use strict;
use warnings;
use POSIX qw(strftime);
use List::Util qw(sum min max);

# ── Log entry structure ───────────────────────────────────────────────────────

package LogEntry;

sub new {
    my ($class, %args) = @_;
    return bless {
        timestamp  => $args{timestamp}  // time(),
        level      => $args{level}      // 'INFO',
        drone_id   => $args{drone_id}   // 'UNKNOWN',
        event_type => $args{event_type} // 'GENERIC',
        message    => $args{message}    // '',
        metadata   => $args{metadata}   // {},
    }, $class;
}

sub to_string {
    my $self = shift;
    return sprintf "[%s] [%s] [%s] %s: %s",
        strftime('%Y-%m-%d %H:%M:%S', localtime($self->{timestamp})),
        $self->{level},
        $self->{drone_id},
        $self->{event_type},
        $self->{message};
}

package LogParser;

# ── Log regex patterns ────────────────────────────────────────────────────────

my %PATTERNS = (
    timestamp   => qr/\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]/,
    level       => qr/\[(DEBUG|INFO|WARN|ERROR|CRITICAL)\]/,
    drone_id    => qr/\[(D\d+|drone_\w+|UNKNOWN)\]/,
    conflict    => qr/CONFLICT:\s*(\w+)\s+severity=([\d.]+)/,
    telemetry   => qr/TELEMETRY:\s*alt=([\d.]+)\s+bat=([\d.]+)\s+vel=([\d.]+)/,
    position    => qr/POS:\s*x=([-\d.]+)\s+y=([-\d.]+)\s+z=([-\d.]+)/,
    battery_low => qr/battery.*?(\d+(?:\.\d+)?)%/i,
    resolution  => qr/RESOLVED:\s*(\w+)\s+method=(\w+)/,
);

sub new {
    my ($class, %opts) = @_;
    return bless {
        entries     => [],
        stats       => { total => 0, by_level => {}, by_drone => {}, errors => 0 },
        filter_level => $opts{filter_level} // 'DEBUG',
        parse_count  => 0,
    }, $class;
}

# Parse a single log line using regex
sub parse_line {
    my ($self, $line) = @_;
    $self->{parse_count}++;

    my %entry_data;

    # Extract timestamp
    if ($line =~ $PATTERNS{timestamp}) {
        $entry_data{timestamp_str} = $1;
    }

    # Extract log level
    if ($line =~ $PATTERNS{level}) {
        $entry_data{level} = $1;
    } else {
        $entry_data{level} = 'INFO';
    }

    # Extract drone ID
    if ($line =~ $PATTERNS{drone_id}) {
        $entry_data{drone_id} = $1;
    } else {
        $entry_data{drone_id} = 'SYSTEM';
    }

    # Parse event-specific data with regex
    my %metadata;
    if ($line =~ $PATTERNS{conflict}) {
        $entry_data{event_type} = 'CONFLICT';
        $metadata{conflict_id} = $1;
        $metadata{severity}    = $2;
    } elsif ($line =~ $PATTERNS{telemetry}) {
        $entry_data{event_type} = 'TELEMETRY';
        $metadata{altitude}  = $1;
        $metadata{battery}   = $2;
        $metadata{velocity}  = $3;
    } elsif ($line =~ $PATTERNS{resolution}) {
        $entry_data{event_type} = 'RESOLVED';
        $metadata{conflict_id} = $1;
        $metadata{method}      = $2;
    } elsif ($line =~ $PATTERNS{battery_low}) {
        $entry_data{event_type} = 'BATTERY_LOW';
        $metadata{battery_pct} = $1;
    } else {
        $entry_data{event_type} = 'GENERIC';
        $entry_data{message}    = $line;
    }

    $entry_data{metadata} = \%metadata;
    $entry_data{message} //= $line;

    my $entry = LogEntry->new(%entry_data);
    $self->_update_stats($entry);
    push @{$self->{entries}}, $entry;
    return $entry;
}

sub _update_stats {
    my ($self, $entry) = @_;
    $self->{stats}{total}++;
    $self->{stats}{by_level}{$entry->{level}}++;
    $self->{stats}{by_drone}{$entry->{drone_id}}++;
    $self->{stats}{errors}++ if $entry->{level} =~ /^(ERROR|CRITICAL)$/;
}

# Analyze parsed log entries
sub analyze {
    my $self = shift;
    my @entries = @{$self->{entries}};

    my @telemetry = grep { $_->{event_type} eq 'TELEMETRY' } @entries;
    my @conflicts = grep { $_->{event_type} eq 'CONFLICT'  } @entries;
    my @resolved  = grep { $_->{event_type} eq 'RESOLVED'  } @entries;

    my %analysis = (
        total_entries    => scalar @entries,
        telemetry_count  => scalar @telemetry,
        conflict_count   => scalar @conflicts,
        resolved_count   => scalar @resolved,
        error_count      => $self->{stats}{errors},
        resolution_rate  => @conflicts > 0 ? scalar(@resolved) / scalar(@conflicts) : 1.0,
        drones_seen      => scalar keys %{$self->{stats}{by_drone}},
    );

    if (@telemetry) {
        my @batteries = map { $_->{metadata}{battery} // 0 } @telemetry;
        @batteries = grep { $_ > 0 } @batteries;
        $analysis{avg_battery} = @batteries ? sum(@batteries) / scalar(@batteries) : 0;
        $analysis{min_battery} = @batteries ? min(@batteries) : 0;
    }

    return \%analysis;
}

# Generate log entries for testing
sub generate_test_log {
    my ($self, $n) = @_;
    $n //= 100;

    my @drone_ids = map { "D$_" } (1..5);
    my @levels    = ('DEBUG', 'INFO', 'INFO', 'INFO', 'WARN', 'ERROR');

    for my $i (1..$n) {
        my $drone_id = $drone_ids[$i % scalar @drone_ids];
        my $level    = $levels[$i % scalar @levels];
        my $t        = time() + $i;
        my $ts       = strftime('%Y-%m-%d %H:%M:%S', localtime($t));
        my $alt      = 95 + int(rand(20));
        my $bat      = 60 + int(rand(40));
        my $vel      = 5  + int(rand(10));
        my $line     = "[$ts] [$level] [$drone_id] TELEMETRY: alt=$alt bat=$bat vel=$vel";
        $self->parse_line($line);
    }

    # Add some conflicts
    for my $i (1..5) {
        my $drone_id = $drone_ids[$i % scalar @drone_ids];
        my $ts       = strftime('%Y-%m-%d %H:%M:%S', localtime(time()));
        my $line     = "[$ts] [WARN] [$drone_id] CONFLICT: CONF_$i severity=0.$i";
        $self->parse_line($line);
    }
}

package LogAnalyzer;

sub new {
    my ($class, $log_path) = @_;
    return bless {
        log_path => $log_path // '/var/log/sdacs/drone.log',
        parser   => LogParser->new(),
        reports  => [],
    }, $class;
}

sub run_analysis {
    my $self = shift;
    $self->{parser}->generate_test_log(100);
    my $analysis = $self->{parser}->analyze();
    push @{$self->{reports}}, $analysis;
    return $analysis;
}

package main;

print "SDACS Log Analyzer v559\n";

my $Analyzer = LogAnalyzer->new();
my $report = $Analyzer->run_analysis();

printf "Total entries: %d\n", $report->{total_entries};
printf "Conflicts: %d | Resolved: %d\n", $report->{conflict_count}, $report->{resolved_count};
printf "Resolution rate: %.2f\n", $report->{resolution_rate};
printf "Average battery: %.1f%%\n", $report->{avg_battery} // 0;
printf "Log parse regex patterns active\n";
