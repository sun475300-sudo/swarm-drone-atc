#!/usr/bin/env perl
# Phase 618 — Perl Log Parser for SDACS simulation logs
# Parses structured log output and extracts metrics

use strict;
use warnings;
use POSIX qw(strftime);

package SDACS::LogParser;

sub new {
    my ($class, %opts) = @_;
    return bless {
        log_file => $opts{log_file} // 'simulation.log',
        events   => [],
        errors   => [],
    }, $class;
}

sub parse_file {
    my ($self, $path) = @_;
    $path //= $self->{log_file};
    open(my $fh, '<', $path) or die "Cannot open $path: $!";
    while (my $line = <$fh>) {
        chomp $line;
        $self->parse_line($line);
    }
    close $fh;
    return $self;
}

sub parse_line {
    my ($self, $line) = @_;
    # Match: [TIMESTAMP] LEVEL drone_id: message
    if ($line =~ /^\[([^\]]+)\]\s+(INFO|WARN|ERROR|DEBUG)\s+(\S+):\s+(.+)$/) {
        my ($ts, $level, $drone, $msg) = ($1, $2, $3, $4);
        my $event = { timestamp => $ts, level => $level, drone => $drone, message => $msg };
        push @{$self->{events}}, $event;
        push @{$self->{errors}}, $event if $level eq 'ERROR';
    }
    # Match CONFLICT lines
    if ($line =~ /CONFLICT\s+(\S+)\s+<->\s+(\S+)\s+dist=([\d.]+)/) {
        push @{$self->{events}}, {
            type   => 'conflict',
            drone1 => $1,
            drone2 => $2,
            dist   => $3 + 0,
        };
    }
}

sub summary {
    my ($self) = @_;
    my $conflicts = grep { ($_->{type} // '') eq 'conflict' } @{$self->{events}};
    return {
        total_events => scalar @{$self->{events}},
        error_count  => scalar @{$self->{errors}},
        conflicts    => $conflicts,
    };
}

1;

package main;
if (!caller) {
    my $parser = SDACS::LogParser->new();
    my $s = $parser->summary();
    printf "Events: %d, Errors: %d, Conflicts: %d\n",
        $s->{total_events}, $s->{error_count}, $s->{conflicts};
}
