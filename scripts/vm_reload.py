import paramiko
import time
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class VBoxController:
    def __init__(self, host=None, username=None, password=None, key_file=None):
        # 환경변수에서 읽기
        self.host = host or os.getenv('VBOX_HOST')
        self.username = username or os.getenv('VBOX_USERNAME')
        self.password = password or os.getenv('VBOX_PASSWORD')
        self.key_file = key_file or os.getenv('VBOX_KEY_FILE')
        
        if not self.host or not self.username:
            raise ValueError("VBOX_HOST와 VBOX_USERNAME은 필수입니다")
    
    def _ssh_command(self, command):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if self.key_file:
                ssh.connect(self.host, username=self.username, key_filename=self.key_file)
            else:
                ssh.connect(self.host, username=self.username, password=self.password)
            
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            ssh.close()
            
            if error and "error" in error.lower():
                raise Exception(f"Command failed: {error}")
            
            return output
        except Exception as e:
            raise Exception(f"SSH 명령 실행 실패: {str(e)}")
    
    def list_vms(self):
        """모든 VM 목록"""
        return self._ssh_command('VBoxManage list vms')
    
    def list_running_vms(self):
        """실행 중인 VM 목록"""
        return self._ssh_command('VBoxManage list runningvms')
    
    def list_snapshots(self, vm_name):
        """VM의 스냅샷 목록"""
        return self._ssh_command(f'VBoxManage snapshot "{vm_name}" list')
    
    def get_vm_info(self, vm_name):
        """VM 상세 정보"""
        return self._ssh_command(f'VBoxManage showvminfo "{vm_name}"')
    
    def get_state(self, vm_name):
        """VM 상태 확인"""
        output = self._ssh_command(f'VBoxManage showvminfo "{vm_name}" --machinereadable')
        for line in output.split('\n'):
            if 'VMState=' in line:
                return line.split('=')[1].strip('"')
        return "unknown"
    
    def start_vm(self, vm_name, gui=False):
        """VM 시작"""
        vm_type = "gui" if gui else "headless"
        print(f"Starting VM: {vm_name} (type: {vm_type})")
        output = self._ssh_command(f'VBoxManage startvm "{vm_name}" --type {vm_type}')
        print(output)
        return output
    
    def stop_vm(self, vm_name, force=False):
        """VM 종료"""
        if force:
            print(f"Force stopping VM: {vm_name}")
            command = f'VBoxManage controlvm "{vm_name}" poweroff'
        else:
            print(f"Gracefully stopping VM: {vm_name}")
            command = f'VBoxManage controlvm "{vm_name}" acpipowerbutton'
        
        output = self._ssh_command(command)
        print(output)
        return output
    
    def pause_vm(self, vm_name):
        """VM 일시정지"""
        print(f"Pausing VM: {vm_name}")
        return self._ssh_command(f'VBoxManage controlvm "{vm_name}" pause')
    
    def resume_vm(self, vm_name):
        """VM 재개"""
        print(f"Resuming VM: {vm_name}")
        return self._ssh_command(f'VBoxManage controlvm "{vm_name}" resume')
    
    def reset_vm(self, vm_name):
        """VM 재시작 (리셋)"""
        print(f"Resetting VM: {vm_name}")
        return self._ssh_command(f'VBoxManage controlvm "{vm_name}" reset')
    
    def save_state(self, vm_name):
        """VM 상태 저장 (하이버네이션)"""
        print(f"Saving state of VM: {vm_name}")
        return self._ssh_command(f'VBoxManage controlvm "{vm_name}" savestate')
    
    def restore_snapshot(self, vm_name, snapshot_name):
        """스냅샷 복원"""
        try:
            # VM이 실행 중이면 종료
            state = self.get_state(vm_name)
            if state == "running":
                print(f"Stopping VM: {vm_name}")
                self.stop_vm(vm_name, force=True)
                time.sleep(3)
            
            # 스냅샷 복원
            print(f"Restoring snapshot: {snapshot_name}")
            output = self._ssh_command(f'VBoxManage snapshot "{vm_name}" restore "{snapshot_name}"')
            print(output)
            time.sleep(2)
            
            return "Success"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def restore_and_start(self, vm_name, snapshot_name, gui=False):
        """스냅샷 복원 후 VM 시작"""
        try:
            # 스냅샷 복원
            result = self.restore_snapshot(vm_name, snapshot_name)
            if "Error" in result:
                return result
            
            # VM 시작
            self.start_vm(vm_name, gui=gui)
            
            return "Success"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_snapshot(self, vm_name, snapshot_name, description=""):
        """새 스냅샷 생성"""
        print(f"Creating snapshot: {snapshot_name}")
        cmd = f'VBoxManage snapshot "{vm_name}" take "{snapshot_name}"'
        if description:
            cmd += f' --description "{description}"'
        return self._ssh_command(cmd)
    
    def delete_snapshot(self, vm_name, snapshot_name):
        """스냅샷 삭제"""
        print(f"Deleting snapshot: {snapshot_name}")
        return self._ssh_command(f'VBoxManage snapshot "{vm_name}" delete "{snapshot_name}"')

    def restore_and_boot_all(self, wait_callback=None):
        """환경변수에서 VM 설정을 읽어 모든 VM 복원 및 부팅"""
        vm_name = os.getenv('VBOX_VM_NAME')
        snapshot_name = os.getenv('VBOX_SNAPSHOT_NAME')
        vm_name_lateral = os.getenv('VBOX_VM_NAME_lateral')
        snapshot_name_lateral = os.getenv('VBOX_SNAPSHOT_NAME_lateral')
        vm_name_ad = os.getenv('VBOX_VM_NAME_ad')
        snapshot_name_ad = os.getenv('VBOX_SNAPSHOT_NAME_ad')

        # AD VM 복원 및 시작
        if vm_name_ad and snapshot_name_ad:
            print(f"  {vm_name_ad} 스냅샷 복원 및 시작 중...")
            self.restore_and_start(vm_name_ad, snapshot_name_ad)
            print(f"  [OK] {vm_name_ad} 재부팅 완료")

        # Main VM 복원 및 시작
        if vm_name and snapshot_name:
            print(f"  {vm_name} 스냅샷 복원 및 시작 중...")
            self.restore_and_start(vm_name, snapshot_name)
            print(f"  [OK] {vm_name} 재부팅 완료")

        # Lateral Movement VM 복원 및 시작
        if vm_name_lateral and snapshot_name_lateral:
            print(f"  {vm_name_lateral} 스냅샷 복원 및 시작 중...")
            self.restore_and_start(vm_name_lateral, snapshot_name_lateral)
            print(f"  [OK] {vm_name_lateral} 재부팅 완료")

        # VM 부팅 대기
        print("  VM 부팅 대기 중 (30초)...")
        time.sleep(30)
        print("  [OK] 모든 VM 재부팅 완료")

        # 콜백 함수 실행 (예: Caldera agent 대기)
        if wait_callback:
            wait_callback()

    def shutdown_all(self):
        """환경변수에서 VM 설정을 읽어 모든 VM 종료"""
        vm_name = os.getenv('VBOX_VM_NAME')
        if vm_name:
            try:
                state = self.get_state(vm_name)
                if state == "running":
                    print(f"[VM 종료] {vm_name} 종료 중...")
                    self.stop_vm(vm_name, force=True)
                    print(f"[OK] {vm_name} 종료 완료")
            except Exception as e:
                print(f"[WARNING] {vm_name} 종료 실패: {e}")

        vm_name_lateral = os.getenv('VBOX_VM_NAME_lateral')
        if vm_name_lateral:
            try:
                state = self.get_state(vm_name_lateral)
                if state == "running":
                    print(f"[VM 종료] {vm_name_lateral} 종료 중...")
                    self.stop_vm(vm_name_lateral, force=True)
                    print(f"[OK] {vm_name_lateral} 종료 완료")
            except Exception as e:
                print(f"[WARNING] {vm_name_lateral} 종료 실패: {e}")

        vm_name_ad = os.getenv('VBOX_VM_NAME_ad')
        if vm_name_ad:
            try:
                state = self.get_state(vm_name_ad)
                if state == "running":
                    print(f"[VM 종료] {vm_name_ad} 종료 중...")
                    self.stop_vm(vm_name_ad, force=True)
                    print(f"[OK] {vm_name_ad} 종료 완료")
            except Exception as e:
                print(f"[WARNING] {vm_name_ad} 종료 실패: {e}")


def main():
    """메인 함수 - 사용 예시"""
    try:
        # 환경변수에서 자동으로 연결 설정 로드
        controller = VBoxController()

        print("=== VM 목록 ===")
        print(controller.list_vms())

        print("\n=== 실행 중인 VM ===")
        print(controller.list_running_vms())

        # 환경변수에서 VM 이름 가져오기
        vm_name = os.getenv('VBOX_VM_NAME')
        snapshot_name = os.getenv('VBOX_SNAPSHOT_NAME')
        vm_name_lateral = os.getenv('VBOX_VM_NAME_lateral')
        snapshot_name_lateral = os.getenv('VBOX_SNAPSHOT_NAME_lateral')

        # Main VM 복원 및 시작
        if vm_name and snapshot_name:
            print(f"\n=== {vm_name} 정보 ===")
            print(f"상태: {controller.get_state(vm_name)}")

            print(f"\n=== {vm_name} 스냅샷 목록 ===")
            print(controller.list_snapshots(vm_name))

            print(f"\n=== {vm_name} 스냅샷 복원 및 시작 ===")
            controller.restore_and_start(vm_name, snapshot_name)

        # Lateral Movement VM 복원 및 시작
        if vm_name_lateral and snapshot_name_lateral:
            print(f"\n=== {vm_name_lateral} 정보 ===")
            print(f"상태: {controller.get_state(vm_name_lateral)}")

            print(f"\n=== {vm_name_lateral} 스냅샷 목록 ===")
            print(controller.list_snapshots(vm_name_lateral))

            print(f"\n=== {vm_name_lateral} 스냅샷 복원 및 시작 ===")
            controller.restore_and_start(vm_name_lateral, snapshot_name_lateral)

        print("\n=== 모든 VM 재부팅 완료 ===")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()