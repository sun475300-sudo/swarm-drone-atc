#!/usr/bin/env perl
# SDACS 로그 파서 — Perl
# ========================
# 시뮬레이션 로그 분석 + 패턴 탐지 + 보고서 생성
#
# 기능:
#   - 구조화/비구조화 로그 파싱
#   - 이상 패턴 탐지 (정규식 기반)
#   - 충돌 이벤트 시퀀스 추출
#   - 통계 요약 생성
#   - CSV/JSON 출력

use strict;
use warnings;
use POSIX qw(strftime);

# ── 로그 레코드 구조 ────────────────────────────────────

package LogRecord;

sub new {
    my ($class, %args) = @_;
    return bless {
        timestamp  => $args{timestamp} // time(),
        level      => $args{level} // 'INFO',
        source     => $args{source} // 'unknown',
        message    => $args{message} // '',
        drone_id   => $args{drone_id},
        event_type => $args{event_type},
        data       => $args{data} // {},
    }, $class;
}

sub to_csv {
    my ($self) = @_;
    return join(',',
        $self->{timestamp},
        $self->{level},
        $self->{source},
        $self->{drone_id} // '',
        $self->{event_type} // '',
        '"' . ($self->{message} =~ s/"/""/gr) . '"'
    );
}

# ── 로그 파서 ────────────────────────────────────────────

package LogParser;

sub new {
    my ($class, %opts) = @_;
    return bless {
        records       => [],
        patterns      => {},
        anomalies     => [],
        stats         => { total => 0, by_level => {}, by_source => {} },
        conflict_seqs => [],
    }, $class;
}

# 정규식 패턴으로 로그 라인 파싱
sub parse_line {
    my ($self, $line) = @_;
    chomp $line;

    # 표준 로그 형식: [TIMESTAMP] LEVEL SOURCE: MESSAGE
    if ($line =~ /^\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]\s+(\w+)\s+(\w+):\s+(.+)$/) {
        my ($ts, $level, $source, $msg) = ($1, $2, $3, $4);

        my $record = LogRecord->new(
            timestamp  => $ts,
            level      => $level,
            source     => $source,
            message    => $msg,
        );

        # 드론 ID 추출
        if ($msg =~ /drone[_\s]?([A-Za-z0-9]+)/i) {
            $record->{drone_id} = "d$1";
        }

        # 이벤트 타입 분류
        $record->{event_type} = $self->classify_event($msg);

        push @{$self->{records}}, $record;
        $self->update_stats($record);
        $self->check_anomaly($record);

        return $record;
    }

    return undef;
}

# 이벤트 분류
sub classify_event {
    my ($self, $msg) = @_;

    my %patterns = (
        'COLLISION'    => qr/collision|impact|crash/i,
        'CONFLICT'     => qr/conflict|cpa|separation/i,
        'ADVISORY'     => qr/advisory|resolution|maneuver/i,
        'EMERGENCY'    => qr/emergency|mayday|critical/i,
        'BATTERY'      => qr/battery|charge|power/i,
        'GPS'          => qr/gps|position|navigation/i,
        'COMM'         => qr/communication|signal|link/i,
        'WEATHER'      => qr/wind|weather|storm/i,
        'NFZ'          => qr/nfz|geofence|restricted/i,
        'TAKEOFF'      => qr/takeoff|launch|depart/i,
        'LANDING'      => qr/landing|touchdown|arrive/i,
        'MISSION'      => qr/mission|waypoint|route/i,
    );

    for my $type (keys %patterns) {
        return $type if $msg =~ $patterns{$type};
    }
    return 'OTHER';
}

# 통계 갱신
sub update_stats {
    my ($self, $record) = @_;
    $self->{stats}{total}++;
    $self->{stats}{by_level}{$record->{level}}++;
    $self->{stats}{by_source}{$record->{source}}++;
}

# 이상 탐지
sub check_anomaly {
    my ($self, $record) = @_;

    # 연속 오류 탐지
    if ($record->{level} eq 'ERROR' || $record->{level} eq 'CRITICAL') {
        push @{$self->{anomalies}}, {
            type      => 'ERROR_SPIKE',
            record    => $record,
            message   => "오류 감지: $record->{message}",
        };
    }

    # 충돌 시퀀스 추적
    if ($record->{event_type} eq 'COLLISION') {
        push @{$self->{conflict_seqs}}, $record;
    }
}

# 파일 전체 파싱
sub parse_file {
    my ($self, $filepath) = @_;
    open my $fh, '<', $filepath or die "Cannot open $filepath: $!";
    while (my $line = <$fh>) {
        $self->parse_line($line);
    }
    close $fh;
    return scalar @{$self->{records}};
}

# 통계 요약
sub summary {
    my ($self) = @_;
    my $stats = $self->{stats};
    return {
        total_records  => $stats->{total},
        by_level       => $stats->{by_level},
        by_source      => $stats->{by_source},
        anomalies      => scalar @{$self->{anomalies}},
        conflict_seqs  => scalar @{$self->{conflict_seqs}},
    };
}

# 보고서 출력
sub print_report {
    my ($self) = @_;
    my $s = $self->summary();

    print "=== SDACS 로그 분석 보고서 ===\n\n";
    printf "총 레코드: %d\n", $s->{total_records};

    print "\n레벨별 분포:\n";
    for my $level (sort keys %{$s->{by_level}}) {
        printf "  %-10s %d\n", $level, $s->{by_level}{$level};
    }

    print "\n소스별 분포:\n";
    for my $src (sort keys %{$s->{by_source}}) {
        printf "  %-15s %d\n", $src, $s->{by_source}{$src};
    }

    printf "\n이상 탐지: %d건\n", $s->{anomalies};
    printf "충돌 시퀀스: %d건\n", $s->{conflict_seqs};
    print "\n=== 분석 완료 ===\n";
}

package main;
1;
