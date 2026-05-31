#!/usr/bin/perl
# P559: LogAnalyzer - Perl drone log analysis
# Phase 559: Parse and analyze SDACS simulation logs with regex patterns

use strict;
use warnings;
use POSIX qw(strftime);
use List::Util qw(sum min max);

# Log entry pattern
my $LOG_PATTERN = qr/
  \[(?<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]  # timestamp
  \s+(?<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)             # log level
  \s+drone=(?<drone_id>[\w-]+)                               # drone ID
  \s+event=(?<event>\w+)                                     # event type
  (?:\s+data=(?<data>.+))?                                   # optional data
/x;

# Conflict pattern
my $CONFLICT_PATTERN = qr/conflict.*drone_a=(\w+).*drone_b=(\w+).*dist=([\d.]+)/i;

# Battery warning pattern
my $BATTERY_PATTERN  = qr/battery.*level=([\d.]+).*drone=(\w+)/i;

package Analyzer;

sub new {
  my ($class, %args) = @_;
  return bless {
    log_file     => $args{log_file} // '/dev/stdin',
    entries      => [],
    errors       => [],
    conflicts    => [],
    battery_alerts => [],
    drone_stats  => {},
  }, $class;
}

sub parse_file {
  my ($self, $file) = @_;
  $file //= $self->{log_file};
  open(my $fh, '<', $file) or die "Cannot open $file: $!";
  while (my $line = <$fh>) {
    chomp $line;
    $self->parse_line($line);
  }
  close($fh);
  return $self;
}

sub parse_line {
  my ($self, $line) = @_;
  if ($line =~ $LOG_PATTERN) {
    my %entry = (
      timestamp => $+{timestamp},
      level     => $+{level},
      drone_id  => $+{drone_id},
      event     => $+{event},
      data      => $+{data} // '',
      raw       => $line,
    );
    push @{$self->{entries}}, \%entry;
    $self->{drone_stats}{$entry{drone_id}}{$entry{event}}++;
    push @{$self->{errors}}, \%entry if $entry{level} eq 'ERROR';
  }
  if ($line =~ $CONFLICT_PATTERN) {
    push @{$self->{conflicts}}, {
      drone_a  => $1,
      drone_b  => $2,
      distance => $3 + 0,
      raw      => $line,
    };
  }
  if ($line =~ $BATTERY_PATTERN) {
    push @{$self->{battery_alerts}}, {
      level    => $1 + 0,
      drone_id => $2,
      raw      => $line,
    };
  }
}

sub report {
  my ($self) = @_;
  my $total = scalar @{$self->{entries}};
  my $errors = scalar @{$self->{errors}};
  my $conflicts = scalar @{$self->{conflicts}};
  return {
    total_entries   => $total,
    error_count     => $errors,
    conflict_count  => $conflicts,
    battery_alerts  => scalar @{$self->{battery_alerts}},
    drones_seen     => scalar keys %{$self->{drone_stats}},
    drone_stats     => $self->{drone_stats},
  };
}

package main;

sub run {
  my $analyzer = Analyzer->new();
  my $report = $analyzer->report();
  printf("Log Analyzer (P559): entries=%d errors=%d conflicts=%d\n",
    $report->{total_entries}, $report->{error_count}, $report->{conflict_count});
  return $report;
}

run() unless caller();
1;
