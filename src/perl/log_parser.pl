#!/usr/bin/perl
# SDACS Phase 618 — Perl ATC log parser
use strict; use warnings;
sub parse_log {
    my ($file) = @_;
    open my $fh, '<', $file or die "Cannot open $file: $!";
    my @events;
    while (<$fh>) {
        push @events, {line => $., text => $_} if /CONFLICT|ADVISORY|COLLISION/;
    }
    return \@events;
}
