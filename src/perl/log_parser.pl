#!/usr/bin/perl
# log_parser.pl - Log file parser for SDACS drone system logs
use strict;
use warnings;
use POSIX qw(strftime);

my %log_counts;
my @events;
my $total_lines = 0;

sub parse_log_line {
    my ($line) = @_;
    $total_lines++;
    if ($line =~ /\[(\w+)\]\s+(\d{4}-\d{2}-\d{2})\s+drone=(\S+)\s+(.+)/) {
        my ($level, $date, $drone_id, $message) = ($1, $2, $3, $4);
        $log_counts{$level}++;
        push @events, {
            level    => $level,
            date     => $date,
            drone_id => $drone_id,
            message  => $message,
        };
    }
}

sub parse_file {
    my ($filename) = @_;
    open(my $fh, '<', $filename) or die "Cannot open $filename: $!";
    while (my $line = <$fh>) {
        chomp $line;
        parse_log_line($line);
    }
    close $fh;
}

sub summarize {
    print "SDACS Log Parser Summary\n";
    print "Total lines: $total_lines\n";
    for my $level (sort keys %log_counts) {
        printf "  %-8s: %d\n", $level, $log_counts{$level};
    }
    printf "Events parsed: %d\n", scalar @events;
}

# Parse stdin or file argument
if (@ARGV) {
    parse_file($ARGV[0]);
} else {
    while (<STDIN>) {
        chomp;
        parse_log_line($_);
    }
}
summarize();
