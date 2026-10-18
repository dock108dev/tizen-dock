using Mono.Cecil;
using System.Reflection.PortableExecutable;
using var asm=AssemblyDefinition.ReadAssembly(args[0]);
var type=asm.MainModule.Types.Single(t=>t.FullName=="ContentsBrowser.CompTerraLayer");
var checkVisible=type.Methods.Single(m=>m.Name=="CheckVisible");
var run=type.Methods.Single(m=>m.Name=="Run");
var visible=checkVisible.Body.Instructions.Select(i=>i.Operand).OfType<MethodReference>().First(m=>m.Name=="set_Visible");
var baseRun=run.Body.Instructions.Select(i=>i.Operand).OfType<MethodReference>().Single(m=>m.Name=="Run" && m.DeclaringType.FullName=="Tizen.TV.Service.CoBA.Core.Component");
var bytes=File.ReadAllBytes(args[0]);
using var pe=new PEReader(new MemoryStream(bytes));
void Patch(MethodDefinition method,byte[] code) {
 if(code.Length>63 || method.Body.CodeSize<code.Length+1)throw new Exception("Unexpected method size");
 var sec=pe.PEHeaders.SectionHeaders.Single(s=>method.RVA>=s.VirtualAddress && method.RVA<s.VirtualAddress+s.VirtualSize);
 int offset=sec.PointerToRawData+method.RVA-sec.VirtualAddress;
 bytes[offset]=(byte)((code.Length<<2)|2);code.CopyTo(bytes,offset+1);
 Console.WriteLine("Patched "+method.FullName);
}
byte[] hide={0x02,0x16,0x28,0,0,0,0,0x2a};
BitConverter.GetBytes(visible.MetadataToken.ToUInt32()).CopyTo(hide,3);
Patch(checkVisible,hide);
byte[] runCode={0x02,0x16,0x28,0,0,0,0,0x02,0x03,0x28,0,0,0,0,0x2a};
BitConverter.GetBytes(visible.MetadataToken.ToUInt32()).CopyTo(runCode,3);
BitConverter.GetBytes(baseRun.MetadataToken.ToUInt32()).CopyTo(runCode,10);
Patch(run,runCode);
Patch(type.Methods.Single(m=>m.Name=="OnBPIEvent"),new byte[]{0x2a});
Patch(type.Methods.Single(m=>m.Name.EndsWith("OnPowerChange")),new byte[]{0x2a});
File.WriteAllBytes(args[1],bytes);
using var reread=AssemblyDefinition.ReadAssembly(args[1]);
var t=reread.MainModule.Types.Single(t=>t.FullName=="ContentsBrowser.CompTerraLayer");
foreach(var m in t.Methods.Where(m=>m.Name is "Run" or "CheckVisible" or "OnBPIEvent" || m.Name.EndsWith("OnPowerChange"))) {
 if(m.Body.ExceptionHandlers.Count!=0)throw new Exception("Unexpected exception sections");
 Console.WriteLine("Verified "+m.Name+": "+string.Join(",",m.Body.Instructions.Select(i=>i.OpCode.Name)));
}
