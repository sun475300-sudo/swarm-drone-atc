#!/usr/bin/perl
# Phase 618: Log Parser — Perl
# SDACS high-performance log file parser for drone telemetry logs

use strict;
use warnings;

package SDACS::LogParser;

my $TIMESTAMP_RE = qr/(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})/;
my $LEVEL_RE     = qr/\[(INFO|WARNING|ERROR|CRITICAL|DEBUG)\]/i;
my $DRONE_RE     = qr/drone[_]?id[=:\s]+([A-Za-z0-9_-]+)/i;

sub new {
    my ($class) = @_;
    return bless { lines => 0, entries => [] }, $class;
}

sub parse_line {
    my ($self, $line) = @_;
    chomp $line;
    my %entry;
    $entry{timestamp} = $1 if $line =~ $TIMESTAMP_RE;
    $entry{level}     = uc($1) if $line =~ $LEVEL_RE;
    $entry{drone_id}  = $1 if $line =~ $DRONE_RE;
    $entry{raw}       = $line;
    $self->{lines}++;
    push @{$self->{entries}}, \%entry;
    return \%entry;
}

sub parse_text {
    my ($self, $text) = @_;
    $self->parse_line($_) for split /\n/, $text;
}

sub summary {
    my $self = shift;
    { total => $self->{lines}, entries => scalar @{$self->{entries}} }
}

package main;
my $parser = SDACS::LogParser->new();
$parser->parse_text("2026-06-01T10:00:00 [INFO] drone_id=D001 battery=85");
my $s = $parser->summary();
printf "Phase 618: Parsed %d lines\n", $s->{total};
