#!/usr/bin/env perl
# log_analyzer.pl
# Phase 559 — Perl log Analyzer for drone telemetry.
# Parses simulation log files using =~ regex matching, aggregates metrics,
# and produces a structured JSON report.

use strict;
use warnings;
use File::Basename qw(basename dirname);
use Getopt::Long   qw(GetOptions);
use POSIX          qw(strftime);
use Scalar::Util   qw(looks_like_number);
use List::Util     qw(min max sum);

# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

my %opt = (
    log     => 'simulation.log',
    out     => '',
    verbose => 0,
    format  => 'text',      # text | json
    phase   => 559,
);

GetOptions(
    'log=s'     => \$opt{log},
    'out=s'     => \$opt{out},
    'verbose!'  => \$opt{verbose},
    'format=s'  => \$opt{format},
) or die "Usage: $0 [--log FILE] [--out FILE] [--verbose] [--format text|json]\n";

# ---------------------------------------------------------------------------
# Regex patterns for log Analyzer
# Phase 559 — =~ matching on structured log lines
# ---------------------------------------------------------------------------

my $RE_TIMESTAMP  = qr/\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]/;
my $RE_LEVEL      = qr/(DEBUG|INFO|WARNING|ERROR|CRITICAL)/;
my $RE_CONFLICT   = qr/CONFLICT\s+drones=\[([^\]]+)\]\s+sep=([\d.]+)m\s+t=([\d.]+)/;
my $RE_COLLISION  = qr/COLLISION\s+drones=\[([^\]]+)\]\s+pos=\(([\d., -]+)\)\s+t=([\d.]+)/;
my $RE_TELEMETRY  = qr/TELEMETRY\s+drone=(\S+)\s+pos=\(([\d., -]+)\)\s+spd=([\d.]+)\s+bat=([\d.]+)/;
my $RE_STATE      = qr/STATE\s+drone=(\S+)\s+(\w+)->(\w+)\s+t=([\d.]+)/;
my $RE_MISSION    = qr/MISSION\s+(START|END|ABORT)\s+id=(\S+)\s+t=([\d.]+)/;

# ---------------------------------------------------------------------------
# Analyzer data structures
# ---------------------------------------------------------------------------

my @conflicts;
my @collisions;
my @state_changes;
my @mission_events;
my %telemetry_last;   # drone_id -> latest telemetry hash
my %drone_speeds;     # drone_id -> [speed samples]

my $lines_parsed  = 0;
my $lines_matched = 0;

# ---------------------------------------------------------------------------
# Core parse routine — uses =~ for all regex matching
# ---------------------------------------------------------------------------

sub parse_log_file {
    my ($fh) = @_;

    while (my $line = <$fh>) {
        chomp $line;
        $lines_parsed++;

        # ── Conflict event
        if ($line =~ $RE_CONFLICT) {
            my ($drones, $sep, $ts) = ($1, $2, $3);
            push @conflicts, {
                drones     => [split /,\s*/, $drones],
                separation => $sep + 0,
                time       => $ts + 0,
            };
            $lines_matched++;
            warn "[559] CONFLICT drones=[$drones] sep=${sep}m\n" if $opt{verbose};
            next;
        }

        # ── Collision event
        if ($line =~ $RE_COLLISION) {
            my ($drones, $pos, $ts) = ($1, $2, $3);
            push @collisions, {
                drones => [split /,\s*/, $drones],
                pos    => $pos,
                time   => $ts + 0,
            };
            $lines_matched++;
            warn "[559] COLLISION drones=[$drones] t=$ts\n" if $opt{verbose};
            next;
        }

        # ── Telemetry line
        if ($line =~ $RE_TELEMETRY) {
            my ($id, $pos, $spd, $bat) = ($1, $2, $3, $4);
            $telemetry_last{$id} = {
                pos     => $pos,
                speed   => $spd + 0,
                battery => $bat + 0,
            };
            push @{ $drone_speeds{$id} }, $spd + 0;
            $lines_matched++;
            next;
        }

        # ── State change
        if ($line =~ $RE_STATE) {
            my ($id, $old, $new, $ts) = ($1, $2, $3, $4);
            push @state_changes, {
                drone => $id,
                from  => $old,
                to    => $new,
                time  => $ts + 0,
            };
            $lines_matched++;
            next;
        }

        # ── Mission event
        if ($line =~ $RE_MISSION) {
            my ($event, $id, $ts) = ($1, $2, $3);
            push @mission_events, {
                event      => $event,
                mission_id => $id,
                time       => $ts + 0,
            };
            $lines_matched++;
            next;
        }
    }
}

# ---------------------------------------------------------------------------
# Metric aggregation
# ---------------------------------------------------------------------------

sub compute_metrics {
    my $n_conflicts  = scalar @conflicts;
    my $n_collisions = scalar @collisions;
    my $total_events = $n_conflicts + $n_collisions;
    my $res_rate     = $total_events > 0
                       ? 1 - $n_collisions / $total_events
                       : 1.0;

    # Mean separation at conflict
    my @seps = map { $_->{separation} } @conflicts;
    my $mean_sep = @seps ? (sum(@seps) / scalar @seps) : 0;

    # Mean speed across all drones
    my @all_speeds = map { @{ $drone_speeds{$_} } } keys %drone_speeds;
    my $mean_speed = @all_speeds ? (sum(@all_speeds) / scalar @all_speeds) : 0;

    return {
        phase           => 559,
        lines_parsed    => $lines_parsed,
        lines_matched   => $lines_matched,
        n_conflicts     => $n_conflicts,
        n_collisions    => $n_collisions,
        resolution_rate => sprintf("%.4f", $res_rate),
        mean_sep_m      => sprintf("%.3f", $mean_sep),
        n_state_changes => scalar @state_changes,
        n_mission_events=> scalar @mission_events,
        n_drones_seen   => scalar(keys %telemetry_last),
        mean_speed_ms   => sprintf("%.3f", $mean_speed),
    };
}

# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

sub print_text_report {
    my ($m) = @_;
    print "=" x 50 . "\n";
    print "[559] Log Analyzer Report — Phase 559\n";
    print "=" x 50 . "\n";
    printf "  Lines parsed     : %d\n",   $m->{lines_parsed};
    printf "  Lines matched    : %d\n",   $m->{lines_matched};
    printf "  Conflicts        : %d\n",   $m->{n_conflicts};
    printf "  Collisions       : %d\n",   $m->{n_collisions};
    printf "  Resolution rate  : %s\n",   $m->{resolution_rate};
    printf "  Mean separation  : %s m\n", $m->{mean_sep_m};
    printf "  State changes    : %d\n",   $m->{n_state_changes};
    printf "  Mission events   : %d\n",   $m->{n_mission_events};
    printf "  Drones seen      : %d\n",   $m->{n_drones_seen};
    printf "  Mean speed       : %s m/s\n", $m->{mean_speed_ms};
    print "=" x 50 . "\n";
}

sub print_json_report {
    my ($m) = @_;
    print "{\n";
    for my $key (sort keys %$m) {
        my $val = $m->{$key};
        if (looks_like_number($val)) {
            printf '  "%s": %s', $key, $val;
        } else {
            printf '  "%s": "%s"', $key, $val;
        }
        print ",\n";
    }
    print '  "_generated": "' . strftime("%Y-%m-%dT%H:%M:%S", localtime) . '"' . "\n";
    print "}\n";
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# Open log file (use synthetic stub data if file is missing)
my $fh;
if (-f $opt{log}) {
    open($fh, '<', $opt{log}) or die "[559] Cannot open '$opt{log}': $!\n";
} else {
    warn "[559] Log file '$opt{log}' not found — using synthetic stub data\n";
    # Inline synthetic log data for demo/testing
    my $stub = <<'STUB';
[2025-05-31T10:00:01] INFO  TELEMETRY drone=D001 pos=(10.0, 20.0, 30.0) spd=4.50 bat=92.0
[2025-05-31T10:00:02] INFO  TELEMETRY drone=D002 pos=(10.5, 20.3, 30.2) spd=4.80 bat=88.0
[2025-05-31T10:00:03] WARNING CONFLICT drones=[D001,D002] sep=3.50m t=3.00
[2025-05-31T10:00:04] INFO  STATE drone=D001 CRUISE->AVOID t=4.00
[2025-05-31T10:00:05] INFO  STATE drone=D002 CRUISE->AVOID t=4.00
[2025-05-31T10:00:07] INFO  STATE drone=D001 AVOID->CRUISE t=7.00
[2025-05-31T10:00:08] INFO  MISSION START id=MISSION-001 t=8.00
[2025-05-31T10:00:09] INFO  TELEMETRY drone=D003 pos=(0.0, 0.0, 50.0) spd=5.10 bat=99.0
[2025-05-31T10:00:15] ERROR COLLISION drones=[D003,D004] pos=(5.0, 5.0, 50.0) t=15.00
[2025-05-31T10:00:20] INFO  MISSION END id=MISSION-001 t=20.00
STUB
    open($fh, '<', \$stub) or die "[559] Cannot open stub: $!\n";
}

parse_log_file($fh);
close $fh;

my $metrics = compute_metrics();

if ($opt{format} eq 'json') {
    print_json_report($metrics);
} else {
    print_text_report($metrics);
}

# Write output file if requested
if ($opt{out}) {
    open(my $ofh, '>', $opt{out}) or die "[559] Cannot write '$opt{out}': $!\n";
    my $old_fh = select $ofh;
    if ($opt{format} eq 'json') {
        print_json_report($metrics);
    } else {
        print_text_report($metrics);
    }
    select $old_fh;
    close $ofh;
    print "[559] Report written to $opt{out}\n";
}

exit 0;
