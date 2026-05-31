#!/usr/bin/env perl
# Log Parser — SDACS Phase 618
use strict;
use warnings;

sub parse_log {
    my ($filename) = @_;
    open(my $fh, '<', $filename) or die "Cannot open: $!";
    my @entries;
    while (<$fh>) {
        chomp;
        push @entries, $_ if /SDACS/;
    }
    close $fh;
    return @entries;
}
1;
