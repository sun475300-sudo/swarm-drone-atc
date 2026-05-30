#!/usr/bin/perl
# SDACS Log Analyzer — Perl (Phase 559)
# 드론 군집 로그 파싱 및 분석 (parse, regex)

use strict;
use warnings;
use POSIX qw(floor);

# 로그 파서 패키지 (Phase 559 Analyzer)
package LogAnalyzer;

sub new {
    my ($class, %opts) = @_;
    return bless {
        patterns  => {},
        records   => [],
        summary   => {},
        severity  => $opts{severity} // 'INFO',
    }, $class;
}

# 패턴 등록
sub add_pattern {
    my ($self, $name, $regex) = @_;
    $self->{patterns}{$name} = qr/$regex/;
}

# 로그 라인 파싱 (regex 활용)
sub parse_line {
    my ($self, $line) = @_;
    chomp $line;
    
    # 기본 타임스탬프 패턴: [2026-05-30 23:10:00] LEVEL drone_id message
    if ($line =~ /^\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]\s+(\w+)\s+(\S+)\s+(.+)$/) {
        my ($ts, $level, $drone_id, $msg) = ($1, $2, $3, $4);
        my $record = {
            timestamp => $ts,
            level     => $level,
            drone_id  => $drone_id,
            message   => $msg,
        };
        
        # 사용자 정의 패턴 매칭
        for my $name (keys %{$self->{patterns}}) {
            if ($msg =~ $self->{patterns}{$name}) {
                $record->{matched_patterns} //= [];
                push @{$record->{matched_patterns}}, $name;
            }
        }
        
        push @{$self->{records}}, $record;
        return $record;
    }
    return undef;
}

# 텍스트 블록 파싱
sub parse {
    my ($self, $text) = @_;
    my @lines = split /\n/, $text;
    my @parsed;
    for my $line (@lines) {
        my $r = $self->parse_line($line);
        push @parsed, $r if defined $r;
    }
    return @parsed;
}

# 요약 생성
sub summarize {
    my ($self) = @_;
    my %by_level;
    my %by_drone;
    my $errors = 0;
    
    for my $r (@{$self->{records}}) {
        $by_level{$r->{level}}++;
        $by_drone{$r->{drone_id}}++;
        $errors++ if $r->{level} =~ /^(ERROR|CRITICAL)$/;
    }
    
    $self->{summary} = {
        total     => scalar @{$self->{records}},
        by_level  => \%by_level,
        by_drone  => \%by_drone,
        errors    => $errors,
    };
    return $self->{summary};
}

sub record_count { scalar @{$_[0]->{records}} }

sub filter_by_level {
    my ($self, $level) = @_;
    return grep { $_->{level} eq $level } @{$self->{records}};
}

sub filter_by_drone {
    my ($self, $drone_id) = @_;
    return grep { $_->{drone_id} eq $drone_id } @{$self->{records}};
}

# 통계 계산
sub error_rate {
    my ($self) = @_;
    my $total = scalar @{$self->{records}};
    return 0.0 unless $total > 0;
    my $errors = grep { $_->{level} =~ /^(ERROR|CRITICAL)$/ } @{$self->{records}};
    return $errors / $total;
}

package main;

# 간단한 CLI
if (!caller()) {
    my $analyzer = LogAnalyzer->new();
    $analyzer->add_pattern('conflict', 'conflict');
    $analyzer->add_pattern('battery',  'battery');
    
    my $sample = "[2026-05-30 23:00:00] INFO  D-001 Flight started at altitude 100m\n" .
                 "[2026-05-30 23:01:00] WARN  D-002 battery level 18%\n" .
                 "[2026-05-30 23:02:00] ERROR D-001 conflict detected with D-003\n";
    
    $analyzer->parse($sample);
    my $s = $analyzer->summarize();
    printf "Records: %d  Errors: %d  Error rate: %.1f%%\n",
        $s->{total}, $s->{errors}, $analyzer->error_rate() * 100;
}

1;
