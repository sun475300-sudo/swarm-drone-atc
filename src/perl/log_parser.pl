#!/usr/bin/perl
# Log Parser — Perl for SDACS audit log processing
# Phase 618

use strict;
use warnings;
use POSIX qw(strftime);

# ── Log Record ───────────────────────────────────────────────────

package LogRecord;

sub new {
    my ($class, %args) = @_;
    return bless {
        timestamp  => $args{timestamp}  // 0,
        level      => $args{level}      // 'INFO',
        actor      => $args{actor}      // '',
        action     => $args{action}     // '',
        details    => $args{details}    // {},
        request_id => $args{request_id} // '',
    }, $class;
}

sub is_error  { $_[0]->{level} eq 'ERROR'   }
sub is_warn   { $_[0]->{level} eq 'WARNING' }
sub is_audit  { $_[0]->{action} =~ /^(LOGIN|LOGOUT|SCENARIO_RUN|ADMIN)/ }

package main;

# ── Parser ───────────────────────────────────────────────────────

sub parse_jsonl {
    my ($filepath) = @_;
    my @records;

    open(my $fh, '<:encoding(UTF-8)', $filepath)
        or die "Cannot open $filepath: $!";

    while (my $line = <$fh>) {
        chomp $line;
        next if $line =~ /^\s*$/;

        # Simple JSON field extraction via regex
        my %fields;
        while ($line =~ /"(\w+)"\s*:\s*"([^"]*?)"/g) {
            $fields{$1} = $2;
        }
        while ($line =~ /"(\w+)"\s*:\s*(\d+(?:\.\d+)?)/g) {
            $fields{$1} = $2 unless exists $fields{$1};
        }

        push @records, LogRecord->new(%fields);
    }
    close($fh);
    return @records;
}

# ── Analysis Functions ───────────────────────────────────────────

sub count_by_level {
    my (@records) = @_;
    my %counts;
    $counts{$_->{level}}++ for @records;
    return %counts;
}

sub filter_by_actor {
    my ($actor, @records) = @_;
    return grep { $_->{actor} eq $actor } @records;
}

sub find_errors {
    my (@records) = @_;
    return grep { $_->is_error() } @records;
}

sub time_range {
    my (@records) = @_;
    return () unless @records;
    my @sorted = sort { $a->{timestamp} <=> $b->{timestamp} } @records;
    return ($sorted[0]->{timestamp}, $sorted[-1]->{timestamp});
}

# ── Report Generation ────────────────────────────────────────────

sub generate_summary {
    my (@records) = @_;
    my %by_level  = count_by_level(@records);
    my @errors    = find_errors(@records);
    my ($t0, $t1) = time_range(@records);

    printf "=== SDACS Log Analysis Report ===\n";
    printf "Total records : %d\n", scalar @records;
    printf "Errors        : %d\n", scalar @errors;
    printf "By level      : %s\n",
        join(', ', map { "$_=$by_level{$_}" } sort keys %by_level);
    if ($t0) {
        printf "Time range    : %s – %s\n",
            strftime('%Y-%m-%dT%H:%M:%SZ', gmtime($t0)),
            strftime('%Y-%m-%dT%H:%M:%SZ', gmtime($t1));
    }
    return { total => scalar @records, errors => scalar @errors, by_level => \%by_level };
}

# ── Main ─────────────────────────────────────────────────────────

unless (caller) {
    my $filepath = shift @ARGV // 'logs/audit.jsonl';
    if (-f $filepath) {
        my @records = parse_jsonl($filepath);
        generate_summary(@records);
    } else {
        print "Usage: $0 [logfile.jsonl]\n";
        print "Log file not found: $filepath\n";
    }
}

1;
