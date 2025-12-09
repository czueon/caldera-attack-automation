#!/usr/bin/env python3
"""
Analyze Collected Outputs
수집된 output을 분석하고 필터링하는 도구
"""

import json
import sys
from typing import Dict, List


class OutputAnalyzer:
    """Output 분석 및 필터링"""
    
    def __init__(self, report_file: str):
        with open(report_file, 'r', encoding='utf-8') as f:
            self.report = json.load(f)
        self.results = self.report['results']
    
    def categorize_outputs(self) -> Dict:
        """Output을 카테고리별로 분류"""
        categories = {
            'substantial': [],      # 실질적인 내용이 많은 output (200자 이상)
            'short': [],            # 짧은 output (10-200자)
            'minimal': [],          # 최소한의 output (10자 미만)
            'empty': [],            # 빈 output
            'error_only': [],       # stderr만 있고 stdout 없음
        }
        
        for result in self.results:
            stdout = result.get('stdout', '')
            stderr = result.get('stderr', '')
            
            if not stdout and stderr:
                categories['error_only'].append(result)
            elif not stdout:
                categories['empty'].append(result)
            elif len(stdout) >= 200:
                categories['substantial'].append(result)
            elif len(stdout) >= 10:
                categories['short'].append(result)
            else:
                categories['minimal'].append(result)
        
        return categories
    
    def analyze_failures(self) -> Dict:
        """실패 케이스 분석"""
        failures = [r for r in self.results if r['status'] != 0]
        
        failure_types = {
            'PERMISSION_ERROR': [],
            'TOOL_MISSING': [],
            'COMMAND_SYNTAX_ERROR': [],
            'ENVIRONMENT_ERROR': [],
            'UNKNOWN': []
        }
        
        for failure in failures:
            stderr = failure.get('stderr', '').lower()
            
            # PERMISSION_ERROR - 더 많은 패턴 추가
            if any(keyword in stderr for keyword in [
                'access denied', 'access is denied', 'permission',
                'access to the path', 'privilege'  # 추가된 패턴
            ]):
                failure_type = 'PERMISSION_ERROR'
            
            # TOOL_MISSING
            elif any(keyword in stderr for keyword in [
                'cannot find', 'does not exist', 'not found',
                'cannot find path', 'no such file'  # 추가된 패턴
            ]):
                failure_type = 'TOOL_MISSING'
            
            # COMMAND_SYNTAX_ERROR
            elif any(keyword in stderr for keyword in [
                'syntax', 'missing mandatory', 'parse',
                'invalid argument', 'invalid parameter'  # 추가된 패턴
            ]):
                failure_type = 'COMMAND_SYNTAX_ERROR'
            
            # ENVIRONMENT_ERROR - 더 많은 패턴 추가
            elif any(keyword in stderr for keyword in [
                'timeout', 'failed to connect', 'not currently available',
                'connection', 'network', 'winrm', 'remote server',  # 추가된 패턴
                'failed with the following error'  # 추가된 패턴
            ]):
                failure_type = 'ENVIRONMENT_ERROR'
            
            # UNKNOWN - stderr이 없거나 패턴 매칭 실패
            else:
                failure_type = 'UNKNOWN'
            
            failure_types[failure_type].append(failure)
        
        return failure_types
    
    def print_summary(self):
        """요약 출력"""
        print(f"{'='*70}")
        print(f"Output Analysis Summary")
        print(f"{'='*70}\n")
        
        # 기본 통계
        stats = self.report.get('statistics', {})
        print(f"Operation: {self.report['operation_metadata']['name']}")
        print(f"Total abilities: {stats.get('total_abilities', len(self.results))}")
        print(f"Success: {stats.get('success', 0)}")
        print(f"Failed: {stats.get('failed', 0)}")
        print(f"Success rate: {stats.get('success_rate', 0)}%")
        
        # Output 통계 (새 형식과 구 형식 호환)
        if 'with_stdout' in stats:
            print(f"\nOutput Statistics:")
            print(f"  With stdout: {stats['with_stdout']}")
            print(f"  With stderr: {stats['with_stderr']}")
            print(f"  With any output: {stats['with_any_output']}/{stats['total_abilities']}")
        elif 'with_output' in stats:
            print(f"With output: {stats['with_output']}/{stats['total_abilities']}")
        
        # Output 카테고리
        print(f"\n{'='*70}")
        print(f"Output Categories")
        print(f"{'='*70}\n")
        
        categories = self.categorize_outputs()
        for category, results in categories.items():
            print(f"{category.upper()}: {len(results)}")
            
            if results:
                for r in results[:3]:
                    print(f"  - {r['ability_name']}")
                    if r.get('stdout'):
                        preview = r['stdout'][:60].replace('\n', ' ')
                        print(f"    Output: {preview}...")
                    elif r.get('stderr'):
                        preview = r['stderr'][:60].replace('\n', ' ')
                        print(f"    Error: {preview}...")
                if len(results) > 3:
                    print(f"  ... and {len(results) - 3} more")
        
        # 실패 분석
        print(f"\n{'='*70}")
        print(f"Failure Analysis (for M7)")
        print(f"{'='*70}\n")
        
        failure_types = self.analyze_failures()
        for ftype, failures in failure_types.items():
            if failures:
                print(f"\n{ftype}: {len(failures)} cases")
                for f in failures[:3]:
                    print(f"  ✗ {f['ability_name']}")
                    if f.get('stderr'):
                        print(f"    Error: {f['stderr'][:100]}...")
    
    def export_filtered(self, output_file: str, min_length: int = 0):
        """필터링된 결과를 새 파일로 저장"""
        filtered_results = [
            r for r in self.results 
            if r.get('stdout') and len(r['stdout']) >= min_length
        ]
        
        filtered_report = self.report.copy()
        filtered_report['results'] = filtered_results
        filtered_report['statistics']['with_detailed_output'] = len(filtered_results)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Filtered report saved: {output_file}")
        print(f"  Original: {len(self.results)} results")
        print(f"  Filtered: {len(filtered_results)} results (>= {min_length} chars)")
    
    def export_failures_only(self, output_file: str):
        """실패 케이스만 저장"""
        failures = [r for r in self.results if r['status'] != 0]
        
        failure_report = {
            'operation_metadata': self.report['operation_metadata'],
            'failure_count': len(failures),
            'failure_types': {},
            'failures': failures
        }
        
        # 실패 타입별 분류
        failure_types = self.analyze_failures()
        for ftype, cases in failure_types.items():
            if cases:
                failure_report['failure_types'][ftype] = len(cases)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(failure_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Failure report saved: {output_file}")
        print(f"  Total failures: {len(failures)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze collected operation outputs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 요약 분석
  python analyze_outputs.py report.json
  
  # 실질적인 output만 필터링 (200자 이상)
  python analyze_outputs.py report.json --filter 200 --output substantial_only.json
  
  # 실패 케이스만 추출
  python analyze_outputs.py report.json --failures-only failures.json
        """
    )
    
    parser.add_argument('report', help='Report JSON file')
    parser.add_argument('--filter', '-f', type=int, metavar='MIN_LENGTH',
                        help='Filter outputs by minimum length')
    parser.add_argument('--output', '-o', help='Output file for filtered results')
    parser.add_argument('--failures-only', '-F', metavar='FILE',
                        help='Export failures only to specified file')
    
    args = parser.parse_args()
    
    # 분석 시작
    analyzer = OutputAnalyzer(args.report)
    
    # 요약 출력
    analyzer.print_summary()
    
    # 필터링
    if args.filter is not None and args.output:
        analyzer.export_filtered(args.output, args.filter)
    
    # 실패만 추출
    if args.failures_only:
        analyzer.export_failures_only(args.failures_only)


if __name__ == '__main__':
    main()
