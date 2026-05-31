#!/usr/bin/env perl
# log_parser.pl
# Perl stub for parsing SDACS simulation log files.
# Extracts conflict events, collision alerts, and drone state transitions.

use strict;
use warnings;
use File::Basename qw(basename);
use Getopt::Long   qw(GetOptions);
use POSIX          qw(strftime);

# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------

my $log_file  = 'simulation.log';
my $out_file  = '';
my $verbose   = 0;

GetOptions(
    'log=s'     => \$log_file,
    'out=s'     => \$out_file,
    'verbose!'  => \$verbose,
) or die "Usage: $0 [--log FILE] [--out FILE] [--verbose]\n";

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

my $RE_CONFLICT  = qr/CONFLICT\s+drone_ids=\[([^\]]+)\]\s+t=([\d.]+)/;
my $RE_COLLISION = qr/COLLISION\s+drone_ids=\[([^\]]+)\]\s+t=([\d.]+)/;
my $RE_STATE     = qr/STATE_CHANGE\s+drone=(\S+)\s+old=(\w+)\s+new=(\w+)\s+t=([\d.]+)/;

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

sub parse_log {
    my ($fh) = @_;
    my @conflicts;
    my @collisions;
    my @state_changes;

    while (my $line = <$fh>) {
        chomp $line;
        if ($line =~ $RE_CONFLICT) {
            push @conflicts, { drones => $1, time => $2 };
            print "[CONFLICT] drones=[$1] t=$2\n" if $verbose;
        }
        elsif ($line =~ $RE_COLLISION) {
            push @collisions, { drones => $1, time => $2 };
            print "[COLLISION] drones=[$1] t=$2\n" if $verbose;
        }
        elsif ($line =~ $RE_STATE) {
            push @state_changes, { drone => $1, old => $2, new => $3, time => $4 };
        }
    }

    return (\@conflicts, \@collisions, \@state_changes);
}

sub print_summary {
    my ($conflicts_ref, $collisions_ref, $states_ref) = @_;
    printf "Conflicts  : %d\n", scalar @$conflicts_ref;
    printf "Collisions : %d\n", scalar @$collisions_ref;
    printf "State chgs : %d\n", scalar @$states_ref;
    my $total = @$conflicts_ref + @$collisions_ref;
    my $res   = $total > 0 ? 1 - @$collisions_ref / $total : 1;
    printf "Resolution : %.2f%%\n", $res * 100;
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

open(my $fh, '<', $log_file) or die "Cannot open log '$log_file': $!\n";
my ($conflicts, $collisions, $states) = parse_log($fh);
close $fh;

print_summary($conflicts, $collisions, $states);

if ($out_file) {
    open(my $ofh, '>', $out_file) or die "Cannot write '$out_file': $!\n";
    printf $ofh "conflicts=%d\ncollisions=%d\n", scalar @$conflicts, scalar @$collisions;
    close $ofh;
    print "Summary written to $out_file\n";
}
