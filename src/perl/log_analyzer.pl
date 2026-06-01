#!/usr/bin/perl
# Phase 559 — Drone Log Analyzer
# Perl script for parsing and analyzing drone operation logs using regex patterns.

use strict;
use warnings;
use POSIX qw(strftime);

# ===== Analyzer Configuration =====

my $VERSION = "1.0.0";
my $LOG_FILE = "drone_operations.log";

# Regex patterns for log line parsing
my %PATTERNS = (
    timestamp   => qr/\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]/,
    drone_id    => qr/DRONE\[(\w+)\]/,
    level       => qr/\b(DEBUG|INFO|WARN|ERROR|CRITICAL)\b/,
    altitude    => qr/ALT:([\d.]+)m/,
    battery     => qr/BAT:([\d.]+)%/,
    gps_coord   => qr/GPS:\(([-\d.]+),([-\d.]+)\)/,
    speed       => qr/SPD:([\d.]+)m\/s/,
    collision   => qr/COLLISION_RISK/i,
    geofence    => qr/GEOFENCE_VIOLATION/i,
    mission     => qr/MISSION_(\w+)/,
);

# ===== Log Record Structure =====

package LogRecord;

sub new {
    my ($class, %args) = @_;
    return bless {
        timestamp   => $args{timestamp}  // '',
        drone_id    => $args{drone_id}   // 'UNKNOWN',
        level       => $args{level}      // 'INFO',
        altitude    => $args{altitude}   // 0.0,
        battery     => $args{battery}    // 100.0,
        speed       => $args{speed}      // 0.0,
        lat         => $args{lat}        // 0.0,
        lon         => $args{lon}        // 0.0,
        raw_line    => $args{raw_line}   // '',
        flags       => $args{flags}      // [],
    }, $class;
}

sub has_flag { return grep { $_ eq $_[1] } @{$_[0]->{flags}} }

package main;

# ===== Log Parser =====

sub parse_line {
    my ($line) = @_;
    my %fields = (raw_line => $line, flags => []);

    # Extract timestamp using =~ regex
    if ($line =~ $PATTERNS{timestamp}) {
        $fields{timestamp} = $1;
    }

    # Extract drone ID
    if ($line =~ $PATTERNS{drone_id}) {
        $fields{drone_id} = $1;
    }

    # Extract log level
    if ($line =~ $PATTERNS{level}) {
        $fields{level} = $1;
    }

    # Extract altitude
    if ($line =~ $PATTERNS{altitude}) {
        $fields{altitude} = $1 + 0.0;
    }

    # Extract battery level
    if ($line =~ $PATTERNS{battery}) {
        $fields{battery} = $1 + 0.0;
    }

    # Extract GPS coordinates using =~ operator
    if ($line =~ $PATTERNS{gps_coord}) {
        $fields{lat} = $1 + 0.0;
        $fields{lon} = $2 + 0.0;
    }

    # Extract speed
    if ($line =~ $PATTERNS{speed}) {
        $fields{speed} = $1 + 0.0;
    }

    # Flag collision risk events
    if ($line =~ $PATTERNS{collision}) {
        push @{$fields{flags}}, 'COLLISION_RISK';
    }

    # Flag geofence violations
    if ($line =~ $PATTERNS{geofence}) {
        push @{$fields{flags}}, 'GEOFENCE_VIOLATION';
    }

    return LogRecord->new(%fields);
}

# ===== Analyzer Class =====

package LogAnalyzer;

sub new {
    my ($class) = @_;
    return bless {
        records     => [],
        errors      => [],
        warnings    => [],
        parse_count => 0,
        stats       => {},
    }, $class;
}

sub parse_lines {
    my ($self, @lines) = @_;
    for my $line (@lines) {
        next unless $line =~ /\S/;  # skip blank lines
        my $rec = main::parse_line($line);
        push @{$self->{records}}, $rec;
        push @{$self->{errors}}, $rec   if $rec->{level} eq 'ERROR';
        push @{$self->{warnings}}, $rec if $rec->{level} eq 'WARN';
        $self->{parse_count}++;
    }
}

sub compute_stats {
    my ($self) = @_;
    my @recs = @{$self->{records}};
    return {} unless @recs;

    my @altitudes = map { $_->{altitude} } @recs;
    my @batteries = map { $_->{battery}  } @recs;
    my @speeds    = map { $_->{speed}    } @recs;

    my $avg = sub {
        my @vals = grep { $_ > 0 } @_;
        return 0 unless @vals;
        my $sum = 0;
        $sum += $_ for @vals;
        return $sum / scalar @vals;
    };

    $self->{stats} = {
        total_records    => scalar @recs,
        total_errors     => scalar @{$self->{errors}},
        total_warnings   => scalar @{$self->{warnings}},
        avg_altitude     => $avg->(@altitudes),
        avg_battery      => $avg->(@batteries),
        avg_speed        => $avg->(@speeds),
        collision_events => scalar(grep { $_->has_flag('COLLISION_RISK') } @recs),
        geofence_events  => scalar(grep { $_->has_flag('GEOFENCE_VIOLATION') } @recs),
        unique_drones    => do {
            my %seen;
            grep { !$seen{$_}++ } map { $_->{drone_id} } @recs;
        },
    };

    return $self->{stats};
}

sub report {
    my ($self) = @_;
    my %s = %{$self->{stats}};
    printf "=== Phase 559: Drone Log Analyzer Report ===\n";
    printf "Total records parsed:  %d\n", $s{total_records}  // 0;
    printf "Errors:                %d\n", $s{total_errors}   // 0;
    printf "Warnings:              %d\n", $s{total_warnings} // 0;
    printf "Avg altitude:          %.1f m\n", $s{avg_altitude}  // 0;
    printf "Avg battery:           %.1f%%\n", $s{avg_battery}   // 0;
    printf "Avg speed:             %.1f m/s\n", $s{avg_speed}   // 0;
    printf "Collision risk events: %d\n", $s{collision_events} // 0;
    printf "Geofence violations:   %d\n", $s{geofence_events}  // 0;
}

package main;

# ===== Synthetic Log Lines for Testing =====

my @sample_logs = (
    "[2025-06-01 10:00:01] DRONE[D001] INFO ALT:55.2m BAT:92.0% SPD:8.5m/s GPS:(37.5665,126.9780)",
    "[2025-06-01 10:00:02] DRONE[D002] INFO ALT:60.0m BAT:88.0% SPD:7.2m/s GPS:(37.5670,126.9785)",
    "[2025-06-01 10:00:05] DRONE[D003] WARN ALT:122.0m BAT:45.0% GEOFENCE_VIOLATION",
    "[2025-06-01 10:00:08] DRONE[D001] ERROR ALT:50.0m BAT:14.0% COLLISION_RISK SPD:12.0m/s",
    "[2025-06-01 10:00:10] DRONE[D004] INFO ALT:58.0m BAT:75.0% SPD:6.0m/s GPS:(37.5680,126.9790)",
    "[2025-06-01 10:00:15] DRONE[D002] WARN ALT:65.0m BAT:40.0% SPD:9.0m/s",
    "[2025-06-01 10:00:20] DRONE[D005] ERROR COLLISION_RISK ALT:52.0m BAT:80.0%",
    "[2025-06-01 10:00:25] DRONE[D001] INFO MISSION_COMPLETE ALT:0.0m BAT:12.0%",
);

# Run the analyzer
my $analyzer = LogAnalyzer->new();
$analyzer->parse_lines(@sample_logs);
$analyzer->compute_stats();
$analyzer->report();

# Extra regex demo: count records matching drone D001
my $d001_count = grep { $_->{drone_id} =~ /^D001$/ } @{$analyzer->{records}};
printf "\nDrone D001 records: %d\n", $d001_count;
printf "Log analysis complete.\n";
