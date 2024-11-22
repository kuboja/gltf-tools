# encoding: UTF-8
### v2015
module TIG
    module Export
        def self.new(typ="glb")
            dir = UI.select_directory(title: "Select folder of SKPs...")
            return unless dir
            dir.tr!("\\", "/")
            puts "#{dir}\n"
            pwd = Dir.pwd
            Dir.chdir(dir)
            Dir.entries(dir).select{|e| e =~ /[.]skp$/ }.each{|skp|
                    nam = skp.gsub(/skp$/, typ)
                    Sketchup.open_file(skp, false)
                    puts "#{skp} >>> #{nam}"
                    Sketchup.active_model.export(nam, false)
            }
            Dir.chdir(pwd)
            puts "\nDone."
        end#def
    end#module
 end#module