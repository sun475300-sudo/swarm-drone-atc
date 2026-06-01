#!/usr/bin/perl
# Log Parser — Perl module for Phase 618
# Advanced drone log parsing utility with structured field extraction.

use strict;
use warnings;
use POSIX qw(floor);

our $VERSION = '1.0.0';

# ===== Log Format Patterns =====

my %FIELD_PATTERNS = (
    timestamp  => qr/\[(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]/,
    drone_id   => qr/(?:DRONE|DRN)\[(\w[-\w]*)\]/,
    log_level  => qr/\b(TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b/i,
    altitude   => qr/(?:ALT|ALTITUDE):([\d.]+)\s*m/i,
    battery    => qr/(?:BAT|BATTERY):([\d.]+)\s*%/i,
    speed      => qr/(?:SPD|SPEED):([\d.]+)\s*m\/s/i,
    gps_lat    => qr/LAT:([-\d.]+)/i,
    gps_lon    => qr/LON:([-\d.]+)/i,
    event_type => qr/\[EVT:([\w_]+)\]/,
    mission_id => qr/MID:([\w-]+)/i,
);

# ===== Field Extractor =====

sub extract_field {
    my ($line, $pattern) = @_;
    return ($line =~ $pattern) ? $1 : undef;
}

sub parse_log_line {
    my ($line) = @_;
    chomp $line;

    my %rec;
    $rec{raw}       = $line;
    $rec{timestamp} = extract_field($line, $FIELD_PATTERNS{timestamp}) // '';
    $rec{drone_id}  = extract_field($line, $FIELD_PATTERNS{drone_id})  // 'UNKNOWN';
    $rec{level}     = extract_field($line, $FIELD_PATTERNS{log_level}) // 'INFO';
    $rec{altitude}  = extract_field($line, $FIELD_PATTERNS{altitude});
    $rec{battery}   = extract_field($line, $FIELD_PATTERNS{battery});
    $rec{speed}     = extract_field($line, $FIELD_PATTERNS{speed});
    $rec{lat}       = extract_field($line, $FIELD_PATTERNS{gps_lat});
    $rec{lon}       = extract_field($line, $FIELD_PATTERNS{gps_lon});
    $rec{event}     = extract_field($line, $FIELD_PATTERNS{event_type});
    $rec{mission}   = extract_field($line, $FIELD_PATTERNS{mission_id});

    # Flag anomalies using =~ regex operator
    $rec{is_error}   = ($line =~ /\b(?:ERROR|CRITICAL|FATAL)\b/i)    ? 1 : 0;
    $rec{collision}  = ($line =~ /COLLISION/i)                         ? 1 : 0;
    $rec{geofence}   = ($line =~ /GEOFENCE/i)                          ? 1 : 0;
    $rec{low_bat}    = (defined $rec{battery} && $rec{battery} < 20)   ? 1 : 0;
    $rec{high_alt}   = (defined $rec{altitude} && $rec{altitude} > 120) ? 1 : 0;

    return \%rec;
}

# ===== Log Parser Class =====

package LogParser;

sub new {
    my ($class, %opts) = @_;
    return bless {
        records    => [],
        errors     => 0,
        warnings   => 0,
        total      => 0,
        filter_lvl => $opts{min_level} // 'DEBUG',
        drone_stats => {},
    }, $class;
}

sub parse {
    my ($self, @lines) = @_;
    for my $line (@lines) {
        next unless $line =~ /\S/;
        my $rec = main::parse_log_line($line);
        push @{$self->{records}}, $rec;
        $self->{total}++;
        $self->{errors}++   if $rec->{is_error};
        $self->{warnings}++ if $rec->{level} =~ /^WARN/i;

        # Accumulate per-drone stats
        my $did = $rec->{drone_id};
        $self->{drone_stats}{$did}{count}++;
        if (defined $rec->{battery}) {
            push @{$self->{drone_stats}{$did}{batteries}}, $rec->{battery};
        }
        if (defined $rec->{altitude}) {
            push @{$self->{drone_stats}{$did}{altitudes}}, $rec->{altitude};
        }
    }
    return $self;
}

sub get_errors {
    my ($self) = @_;
    return grep { $_->{is_error} } @{$self->{records}};
}

sub get_events {
    my ($self, $event_type) = @_;
    return grep { defined $_->{event} && $_->{event} eq $event_type } @{$self->{records}};
}

sub drone_summary {
    my ($self, $drone_id) = @_;
    my $s = $self->{drone_stats}{$drone_id} or return {};
    my @bats = @{$s->{batteries} // []};
    my @alts = @{$s->{altitudes} // []};
    my $avg_bat = @bats ? (do { my $sum = 0; $sum += $_ for @bats; $sum / @bats }) : 'N/A';
    my $avg_alt = @alts ? (do { my $sum = 0; $sum += $_ for @alts; $sum / @alts }) : 'N/A';
    return {
        drone_id => $drone_id,
        count    => $s->{count} // 0,
        avg_bat  => ref $avg_bat ? $avg_bat : sprintf("%.1f", $avg_bat),
        avg_alt  => ref $avg_alt ? $avg_alt : sprintf("%.1f", $avg_alt),
    };
}

sub report {
    my ($self) = @_;
    printf "=== Phase 618: Log Parser Report ===\n";
    printf "Total records:   %d\n", $self->{total};
    printf "Errors:          %d\n", $self->{errors};
    printf "Warnings:        %d\n", $self->{warnings};
    printf "Unique drones:   %d\n", scalar keys %{$self->{drone_stats}};
    printf "\nPer-drone summary:\n";
    for my $did (sort keys %{$self->{drone_stats}}) {
        my $s = $self->drone_summary($did);
        printf "  %s: %d records | avg_bat=%s%% | avg_alt=%sm\n",
            $did, $s->{count}, $s->{avg_bat}, $s->{avg_alt};
    }
}

package main;

# ===== Sample Log Data =====

my @sample_logs = (
    "[2025-06-01 10:00:01] DRONE[D001] INFO ALT:55.2m BAT:92.0% SPD:8.5m/s LAT:37.5665 LON:126.9780 MID:M001",
    "[2025-06-01 10:00:02] DRONE[D002] INFO ALT:60.0m BAT:88.0% SPD:7.2m/s MID:M001",
    "[2025-06-01 10:00:05] DRONE[D003] WARN ALT:122.0m BAT:45.0% GEOFENCE_VIOLATION [EVT:GEOFENCE_BREACH]",
    "[2025-06-01 10:00:08] DRONE[D001] ERROR ALT:50.0m BAT:14.0% COLLISION_RISK SPD:12.0m/s",
    "[2025-06-01 10:00:10] DRONE[D004] INFO ALT:58.0m BAT:75.0% SPD:6.0m/s LAT:37.5680 LON:126.9790",
    "[2025-06-01 10:00:15] DRONE[D002] WARN ALT:65.0m BAT:18.5% SPD:9.0m/s [EVT:LOW_BATTERY]",
    "[2025-06-01 10:00:20] DRONE[D005] CRITICAL COLLISION_RISK ALT:52.0m BAT:80.0% [EVT:COLLISION]",
    "[2025-06-01 10:00:25] DRONE[D001] INFO [EVT:MISSION_COMPLETE] ALT:0.0m BAT:12.0% MID:M001",
    "[2025-06-01 10:00:30] DRONE[D003] DEBUG ALT:70.0m BAT:70.0% SPD:5.5m/s",
    "[2025-06-01 10:00:35] DRONE[D004] INFO ALT:62.0m BAT:68.0% SPD:7.8m/s MID:M002",
);

# ===== Run Parser =====

my $parser = LogParser->new(min_level => 'DEBUG');
$parser->parse(@sample_logs);
$parser->report();

# Extra: find collision events using =~ regex
my @collisions = grep { $_->{collision} } @{$parser->{records}};
printf "\nCollision risk events: %d\n", scalar @collisions;

# Filter records by drone using regex
my @d001_recs = grep { $_->{drone_id} =~ /^D001$/ } @{$parser->{records}};
printf "D001 log entries: %d\n", scalar @d001_recs;
printf "Parse complete.\n";
