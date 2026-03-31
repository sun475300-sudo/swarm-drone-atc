#!/usr/bin/perl
# Phase 618: Log Parser — Perl Regex Flight Log Parser
# 대용량 비행 로그 정규식 파서

use strict;
use warnings;
use Time::Piece;

# ── Log Entry Structure ──
package LogEntry;
sub new {
    my ($class, %args) = @_;
    return bless {
        timestamp => $args{timestamp} // '',
        level     => $args{level}     // 'INFO',
        drone_id  => $args{drone_id}  // '',
        event     => $args{event}     // '',
        details   => $args{details}   // '',
        raw       => $args{raw}       // '',
    }, $class;
}

# ── Log Parser ──
package LogParser;

sub new {
    my ($class) = @_;
    return bless {
        entries       => [],
        error_count   => 0,
        warning_count => 0,
        lines_parsed  => 0,
        patterns      => {
            standard  => qr/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+\[(\w+)\]\s+drone_(\d+)\s+(\w+):\s*(.*)$/,
            conflict  => qr/CONFLICT\s+drone_(\d+)\s+<->\s+drone_(\d+)\s+dist=(\d+\.?\d*)/,
            advisory  => qr/ADVISORY\s+drone_(\d+)\s+type=(\w+)\s+severity=(\w+)/,
            battery   => qr/BATTERY\s+drone_(\d+)\s+level=(\d+\.?\d*)%/,
            position  => qr/POS\s+drone_(\d+)\s+x=(-?\d+\.?\d*)\s+y=(-?\d+\.?\d*)\s+z=(-?\d+\.?\d*)/,
        },
    }, $class;
}

sub parse_line {
    my ($self, $line) = @_;
    chomp $line;
    $self->{lines_parsed}++;

    if ($line =~ $self->{patterns}{standard}) {
        my $entry = LogEntry->new(
            timestamp => $1,
            level     => $2,
            drone_id  => "drone_$3",
            event     => $4,
            details   => $5,
            raw       => $line,
        );
        push @{$self->{entries}}, $entry;
        $self->{error_count}++   if $entry->{level} eq 'ERROR';
        $self->{warning_count}++ if $entry->{level} eq 'WARN';
        return $entry;
    }
    return undef;
}

sub parse_file {
    my ($self, $filename) = @_;
    open(my $fh, '<', $filename) or die "Cannot open $filename: $!";
    while (my $line = <$fh>) {
        $self->parse_line($line);
    }
    close($fh);
    return scalar @{$self->{entries}};
}

sub extract_conflicts {
    my ($self) = @_;
    my @conflicts;
    for my $entry (@{$self->{entries}}) {
        if ($entry->{raw} =~ $self->{patterns}{conflict}) {
            push @conflicts, {
                drone_a  => "drone_$1",
                drone_b  => "drone_$2",
                distance => $3 + 0,
            };
        }
    }
    return \@conflicts;
}

sub extract_advisories {
    my ($self) = @_;
    my @advisories;
    for my $entry (@{$self->{entries}}) {
        if ($entry->{raw} =~ $self->{patterns}{advisory}) {
            push @advisories, {
                drone_id => "drone_$1",
                type     => $2,
                severity => $3,
            };
        }
    }
    return \@advisories;
}

sub get_summary {
    my ($self) = @_;
    return {
        lines_parsed  => $self->{lines_parsed},
        entries       => scalar @{$self->{entries}},
        errors        => $self->{error_count},
        warnings      => $self->{warning_count},
    };
}

1;
